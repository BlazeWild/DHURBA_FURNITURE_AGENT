import re
from langchain_core.tools import tool
from typing import Dict, Any

# Route definitions with keywords for intelligent LLM routing
ROUTE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Authentication-required routes
    "profile": {
        "path": "/profile-settings",
        "auth_required": True,
        "title": "Profile Settings",
        "description": "View and manage your profile information",
        "keywords": ["profile", "my profile", "profile settings", "account settings", "my account", "user profile", "personal info", "account info", "who am i", "my info", "my details"]
    },
    "cart": {
        "path": "/cart",
        "auth_required": True,
        "title": "Shopping Cart",
        "description": "View and manage items in your cart",
        "keywords": ["cart", "shopping cart", "my cart", "basket", "my basket", "cart items", "what's in my cart", "show my cart", "cart page", "shopping basket"]
    },
    # Public routes
    "home": {
        "path": "/",
        "auth_required": False,
        "title": "Homepage",
        "description": "Welcome to Dhurba Furniture Store",
        "keywords": ["home", "homepage", "main page", "welcome", "start", "beginning", "dhurba", "furniture store"]
    },
    "shop": {
        "path": "/shop",
        "auth_required": False,
        "title": "All Products",
        "description": "Browse our complete furniture catalog",
        "keywords": ["shop", "browse", "products", "all products", "catalog", "furniture", "what do you have", "show me products", "browse products", "store", "shopping"]
    },
    "products": {
        "path": "/shop",
        "auth_required": False,
        "title": "All Products", 
        "description": "Browse our complete furniture catalog",
        "keywords": ["products", "all products", "product catalog", "browse products", "show products", "furniture catalog", "items", "merchandise"]
    },
    # Auth routes
    "login": {
        "path": "/login",
        "auth_required": False,
        "title": "Login",
        "description": "Sign in to your account",
        "keywords": ["login", "log in", "sign in", "signin", "authenticate", "enter account", "access account", "help me login"]
    },
    "signup": {
        "path": "/signup",
        "auth_required": False,
        "title": "Sign Up",
        "description": "Create a new account",
        "keywords": ["signup", "sign up", "register", "registration", "create account", "new account", "join", "become member"]
    },
    # Dynamic product route template
    "product-details": {
        "path": "/product/{slug}",
        "auth_required": False,
        "title": "Product Details",
        "description": "View detailed product information",
        "keywords": ["product details", "more details", "specific product", "product page", "item details", "tell me more", "show details", "product info"]
    }
}

def slugify(text: str) -> str:
    """Converts a string to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    return text.strip('-')

def normalize_product_name(text: str) -> str:
    """
    Minimal normalization for LLM-powered product matching.
    The LLM agent should use db_query tool to intelligently find products,
    not rely on hardcoded pattern matching.
    """
    if not text:
        return ""
    
    # Basic cleanup only - let the LLM + database do the intelligent matching
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)  # Remove special chars except hyphens
    
    # Handle common size variations
    text = re.sub(r'\b(king|queen|twin|full|double)\s*size\b', r'\1-sized', text)
    
    text = re.sub(r'\s+', '-', text)      # Convert spaces to hyphens
    text = re.sub(r'-+', '-', text)       # Remove multiple hyphens
    text = text.strip('-')                # Remove leading/trailing hyphens
    return text

def match_query_to_route_keyword(query: str) -> str:
    """
    Intelligent matching of user queries to route keywords using LLM-friendly keyword matching.
    This helps the LLM agent automatically determine the best route_keyword for user requests.
    
    Args:
        query (str): User's query or request
        
    Returns:
        str: Best matching route_keyword or "shop" as default
    """
    if not query:
        return "shop"
    
    query_lower = query.lower().strip()
    
    # Direct keyword matching for each route
    for route_keyword, route_info in ROUTE_DEFINITIONS.items():
        if "keywords" in route_info:
            for keyword in route_info["keywords"]:
                if keyword.lower() in query_lower:
                    return route_keyword
    
    # Fallback patterns for common requests
    profile_patterns = ["who am i", "my info", "my details", "user info"]
    cart_patterns = ["cart", "basket", "my items"]
    login_patterns = ["login", "log in", "sign in"]
    
    for pattern in profile_patterns:
        if pattern in query_lower:
            return "profile"
    
    for pattern in cart_patterns:
        if pattern in query_lower:
            return "cart"
    
    for pattern in login_patterns:
        if pattern in query_lower:
            return "login"
    
    # Default to shop for product-related or general queries
    return "shop"

@tool
def route_to_page(route_keyword: str = None, slug: str = None, user_authenticated: bool = False, category: str = None, room: str = None) -> str:
    """
    Intelligent routing tool that navigates users to different pages in the furniture store.
    This tool automatically opens pages in VS Code Simple Browser for seamless navigation.
    
    Available route_keywords:
    - "profile": User profile/settings page (requires auth)
    - "cart": Shopping cart page (requires auth)  
    - "shop": Browse all products page
    - "products": Browse all products page (same as shop)
    - "login": Login page
    - "signup": Sign up/registration page
    - "home": Homepage
    - "product-details": Specific product page (requires slug)
    
    Examples:
    - route_keyword="profile" → Opens profile settings page
    - route_keyword="cart" → Opens shopping cart
    - route_keyword="shop" → Opens product catalog
    - route_keyword="login" → Opens login page
    - route_keyword="product-details", slug="accent-chair" → Opens specific product    Args:
        route_keyword (str): The specific route to navigate to
        slug (str): Product slug for product-details route
        user_authenticated (bool): Whether user is authenticated
        category (str): Product category filter for shop page
        room (str): Room type filter for shop page
        
    Returns:
        str: Navigation result with URL and status
    """
    import subprocess
    import logging
    
    logger = logging.getLogger(__name__)
    
    # If no route_keyword provided, default to home
    if not route_keyword:
        route_keyword = "home"
    
    # Check if route exists
    if route_keyword not in ROUTE_DEFINITIONS:
        # If invalid route_keyword, default to shop for product-related queries
        route_keyword = "shop"
    
    route_info = ROUTE_DEFINITIONS[route_keyword]
    
    # Handle authentication requirements
    if route_info["auth_required"] and not user_authenticated:
        # Redirect to login if auth required but user not authenticated
        final_url = ROUTE_DEFINITIONS['login']['path']
        navigation_msg = f"🔒 Authentication required! Taking you to login page"
    else:
        # Build the final URL
        if route_keyword == "product-details":
            if not slug:
                # If no slug provided for product details, redirect to shop
                final_url = ROUTE_DEFINITIONS['shop']['path']
                navigation_msg = "📦 No specific product provided, showing all products"
            else:
                final_url = f"/product/{slug}"
                navigation_msg = f"🛋️ Opening product details for {slug}"
        elif route_keyword in ["shop", "products"]:
            # Handle shop with filters
            shop_url = ROUTE_DEFINITIONS['shop']['path']
            params = []
            if category:
                params.append(f"category={category.replace(' ', '+')}")
            if room:
                params.append(f"room={room.replace(' ', '+')}")
            if params:
                final_url = f"{shop_url}?{'&'.join(params)}"
                navigation_msg = f"🏪 Browsing {category or room or 'products'}"
            else:
                final_url = shop_url
                navigation_msg = "🏪 Opening product catalog"
        else:
            # Standard route
            final_url = route_info['path']
            navigation_msg = f"📄 Opening {route_info['title']}"    # Return the navigation result with URL - ChatbotOverlay.jsx will handle the actual navigation
    return f"{navigation_msg}\n🌐 {final_url}"
