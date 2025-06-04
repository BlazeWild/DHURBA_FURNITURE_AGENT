from langchain_core.messages import HumanMessage, ToolMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode, tools_condition
import os
import logging
import asyncio
import argparse
import sys
import uuid
from typing_extensions import Literal
from agent.utils.tools import validate_user_authentication, get_user_profile_data, update_user_profile
from agent.utils.product_tools import query_db
from agent.utils.routing_tools import route_to_page
from agent.utils.cart_tools import get_user_cart_data, add_item_to_cart, update_cart_item
from agent.utils.prompt import system_prompt
from agent.utils.rag_tool import rag_tool

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LLM Setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    api_key=GOOGLE_API_KEY,
    temperature=0.5,  # Reduced for faster, more focused responses
    max_tokens=800,  # Increased to allow proper tool calling
)

# OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# llm= ChatLiteLLM(
#     model="openrouter/deepseek/deepseek-chat-v3-0324:free",
#     api_key=OPENROUTER_API_KEY,
#     temperature=0.3,  # Reduced for faster, more focused responses
#     max_tokens=200,
#     max_retries=5,
# )

# tools = await client.get_tools()
tools = [
    validate_user_authentication,
    get_user_profile_data,
    query_db,
    route_to_page,  # URL generation and routing logic
    get_user_cart_data,
    add_item_to_cart,
    update_cart_item,
    update_user_profile,
    rag_tool,  # RAG tool for retrieving relevant documents
]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)

# Nodes
def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or not."""
    return {
        "messages": [
            llm_with_tools.invoke(
                [SystemMessage(content=system_prompt)]
                + state["messages"]
            )
        ]
    }

def tool_node(state: dict):
    """Performs the tool call with proper error handling."""
    result = []
    for tool_call in state["messages"][-1].tool_calls:
        try:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            result.append(ToolMessage(content=str(observation), tool_call_id=tool_call["id"]))
            logger.info(f"Tool {tool_call['name']} executed successfully")
        except Exception as e:
            error_msg = f"Error executing tool {tool_call['name']}: {str(e)}"
            logger.error(error_msg)
            result.append(ToolMessage(content=error_msg, tool_call_id=tool_call["id"]))
    return {"messages": result}

def should_continue(state: MessagesState) -> Literal["Action", "END"]:
    """
    Decide if we should continue the loop or stop based on
    whether the LLM made a tool call.
    """
    messages = state["messages"]
    last_message = messages[-1]

    if last_message.tool_calls:
        return "Action"
    return "END"

# Build workflow
agent_builder = StateGraph(MessagesState)
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("environment", tool_node)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    {
        "Action": "environment",
        "END": END,
    },
)
agent_builder.add_edge("environment", "llm_call")

# Compile the agent (LangGraph API handles persistence automatically)
agent = agent_builder.compile()
