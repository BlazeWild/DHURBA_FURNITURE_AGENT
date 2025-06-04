from sqlalchemy import create_engine, text, Engine
import pandas as pd
from langchain_core.tools import tool
from dotenv import load_dotenv
import os
load_dotenv()



# --- ServerSession and DB Tools ---
class ServerSession:
    """A session for server-side state management and operations.
    In practice, this would be a separate service from where the agent is running and the agent would communicate with it using a REST API. In this simplified example, we use it to persist the db engine and data returned from the query_db tool.
    """
    def __init__(self):
        self.engine: Engine = None
        self.df: pd.DataFrame = None
        # Lazy initialization - don't connect until needed
        self._initialized = False
    
    def _ensure_connected(self):
        """Ensure database connection is established"""
        if self._initialized:
            return
            
        try:
            supabase_url = os.getenv("SUPABASE_URL")
            print(f"Connecting to database at {supabase_url}")
            self.engine = create_engine(
                supabase_url,
                pool_size=2,          # Reduced pool size for faster startup
                max_overflow=2,       # Reduced overflow
                pool_timeout=5,       # Reduced timeout
                pool_recycle=1800,
                pool_pre_ping=True,
                pool_use_lifo=True,
                connect_args={
                    "application_name": "furniture",
                    "options": "-c statement_timeout=10000",  # Reduced timeout
                    "keepalives": 1,
                    "keepalives_idle": 60,
                    "keepalives_interval": 30,
                    "keepalives_count": 3
                }
            )
            self._initialized = True
            print("✅ Database connection established")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise

# Create a global instance of the ServerSession
session = ServerSession()

@tool
def query_db(query: str) -> str:
    """Query the database using Postgres SQL - ONLY for products and featured_products tables.
    Args:
        query: The SQL query to execute. Must be a valid postgres SQL string that can be executed directly.
               ONLY queries on 'products' and 'featured_products' tables are allowed.
    Returns:
        str: Raw query results that the LLM will format appropriately.
    """
    try:
        # Ensure database connection is established
        session._ensure_connected()
        
        # Validate that query only contains allowed tables
        query_lower = query.lower()
        allowed_tables = ['products', 'featured_products']
        forbidden_tables = ['users', 'auth', 'profiles', 'orders', 'payments', 'admin']
        
        has_allowed_table = any(table in query_lower for table in allowed_tables)
        has_forbidden_table = any(table in query_lower for table in forbidden_tables)
        
        if has_forbidden_table:
            return "Error: Query contains forbidden tables. Only 'products' and 'featured_products' tables are allowed."
        
        if not has_allowed_table:
            return "Error: Query must reference 'products' or 'featured_products' tables."
        
        with session.engine.connect().execution_options(
            isolation_level="READ COMMITTED"
        ) as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = result.fetchall()
            df = pd.DataFrame(rows, columns=columns)            # Store the raw results including slug for LLM internal use
            session.df = pd.DataFrame(rows, columns=columns)
            
            # Create user-friendly display without image_url (keep product_id for cart operations)
            display_fields = ['image_url']  # Only hide image_url, keep product_id for cart tools
            df_display = df.drop(columns=[col for col in display_fields if col in df.columns])
            
            conn.close()
            
            # Return both display format and internal data
            display_result = df_display.to_markdown(index=False)
              # Add slug and product_id information as hidden metadata for LLM routing and cart operations
            if 'slug' in df.columns and not df.empty:
                slug_info = "\n\n[INTERNAL_SLUG_DATA]:"
                for _, row in df.iterrows():
                    if 'name' in row and 'slug' in row:
                        slug_info += f"\n- {row['name']}: {row['slug']}"
                display_result += slug_info
            
            # Add product_id information as hidden metadata for cart operations
            if 'product_id' in df.columns and not df.empty:
                product_id_info = "\n\n[INTERNAL_PRODUCT_ID_DATA]:"
                for _, row in df.iterrows():
                    if 'name' in row and 'product_id' in row:
                        product_id_info += f"\n- {row['name']}: {row['product_id']}"
                display_result += product_id_info
            
            return display_result
    except Exception as e:
        return f"Error executing query: {str(e)}"