import os
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

# Global variable to store the initialized tool
_rag_tool_instance = None
_initialization_failed = False

@tool
def rag_tool(query: str) -> str:
    """Searches and returns relevant information about Dhurba Furniture Store including furniture FAQs, policies, customization options, history, delivery, warranty, and general furniture-related questions."""
    global _rag_tool_instance, _initialization_failed
    
    # If initialization previously failed, return fallback message
    if _initialization_failed:
        return """I'm sorry, but I cannot access our knowledge database right now due to a technical issue. However, I can still assist you with:

🛋️ **Product Information:**
- Browse our furniture collections by room (bedroom, living room, dining room, office)
- Search for specific items like beds, sofas, tables, chairs
- View product details and pricing

🛒 **Shopping Assistance:**
- Add items to your cart
- Manage your cart contents
- Navigate to different store sections

👤 **Account Management:**
- View and update your profile
- Check your cart status

📞 **For store policies, delivery info, warranties, or customization options:**
Please contact our customer support team directly - they'll have all the detailed information you need!

**How can I help you shop for furniture today?** Try asking "show me bedroom furniture" or "find dining tables"."""
    
    # If not initialized yet, try to initialize
    if _rag_tool_instance is None:
        try:
            # Import here to avoid hanging during module import
            from langchain_pinecone import PineconeVectorStore
            # Use the legacy import that matches your working notebook
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_core.tools import create_retriever_tool
            
            PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
            
            if not PINECONE_API_KEY:
                raise Exception("PINECONE_API_KEY not found in environment variables")
            
            # Initialize embeddings (matching your working notebook)
            embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"}
            )
            
            index_name = "dhurba-furniture-rag"
            
            # Connect to Pinecone (matching your working notebook)
            vectorstore = PineconeVectorStore(
                index_name=index_name,
                embedding=embeddings,
                pinecone_api_key=PINECONE_API_KEY
            )
            
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})  # Get more relevant docs
            
            _rag_tool_instance = create_retriever_tool(
                retriever,
                "search_furniture_knowledge_base",
                "Searches Dhurba Furniture Store's knowledge base for information about furniture care, policies, customization, delivery, warranty, FAQs, and general furniture information."
            )
            
        except Exception as e:
            _initialization_failed = True
            return f"I'm sorry, but I cannot access our knowledge database right now. The system encountered an error: {str(e)}. I can still help you with product searches and navigation. Please ask about specific products or let me know how else I can assist you."
    
    # Use the initialized tool
    try:
        result = _rag_tool_instance.invoke(query)
        
        # If no relevant results found, provide helpful fallback
        if not result or len(str(result).strip()) < 20:
            return "I couldn't find specific information about that in our knowledge base, but I'd be happy to help you in other ways!"
        
        return result
        
    except Exception as e:
        return f"I encountered a technical issue while searching our knowledge base. But I'm still here to help you shop!"

