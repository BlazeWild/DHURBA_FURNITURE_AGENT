import requests
import logging
from typing import Dict, Any
import os
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL for the backend API
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

@tool
def get_user_cart_data(user_id: str) -> Dict[str, Any]:
    """
    Fetches user cart data for authenticated users.
    
    Args:
        user_id: The user ID to fetch cart data for
        
    Returns:
        Dict containing cart data and success status
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.info("No user ID provided for cart data fetch")
            return {
                "success": False,
                "message": "No user session found. Please log in to view your cart.",
                "user_id": None,
                "cart_data": None
            }
            
        logger.info(f"Fetching cart data for user: {user_id}")
        
        # Call the simple backend cart endpoint (no JWT needed)
        url = f"{BACKEND_BASE_URL}/api/cart/user/{user_id}"
        response = requests.get(url, timeout=60)
        
        if response.status_code == 200:
            cart_data = response.json()
            logger.info(f"[SUCCESS] Successfully retrieved cart for user: {user_id}")
            return {
                "success": True,
                "message": "Cart data retrieved successfully",
                "user_id": user_id,
                "cart_data": cart_data
            }
        elif response.status_code == 404:
            logger.info(f"[ERROR] Cart not found for user: {user_id}")
            return {
                "success": False,
                "message": "Cart not found. You don't have any items in your cart yet.",
                "user_id": user_id,
                "cart_data": None
            }
        else:
            logger.warning(f"[ERROR] Cart fetch failed: {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to retrieve cart data. Please try again.",
                "user_id": user_id,
                "cart_data": None
            }
            
    except Exception as e:
        logger.error(f"Error fetching user cart: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving cart: {str(e)}",
            "user_id": user_id,
            "cart_data": None
        }

@tool
def add_item_to_cart(user_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Adds an item to the user's cart.
    
    Args:
        user_id: The user ID
        product_id: The product ID to add to cart
        quantity: The quantity to add (default: 1)
        
    Returns:
        Dict containing updated cart data and success status
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            return {
                "success": False,
                "message": "No user session found. Please log in to add items to your cart.",
                "user_id": None,
                "cart_data": None
            }
            
        if not product_id:
            return {
                "success": False,
                "message": "Product ID is required to add item to cart.",
                "user_id": user_id,
                "cart_data": None
            }
            
        if quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than 0.",
                "user_id": user_id,
                "cart_data": None
            }
            
        logger.info(f"Adding item to cart for user: {user_id}, product: {product_id}, quantity: {quantity}")
        
        # Call the simple backend cart endpoint (no JWT needed)
        url = f"{BACKEND_BASE_URL}/api/cart/user/{user_id}/items"
        headers = {"Content-Type": "application/json"}
        data = {
            "product_id": product_id,
            "quantity": quantity
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            cart_data = response.json()
            logger.info(f"[SUCCESS] Successfully added item to cart for user: {user_id}")
            return {
                "success": True,
                "message": f"Successfully added {quantity} item(s) to your cart.",
                "user_id": user_id,
                "cart_data": cart_data
            }
        else:
            logger.warning(f"[ERROR] Add to cart failed: {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to add item to cart. Please try again.",
                "user_id": user_id,
                "cart_data": None
            }
            
    except Exception as e:
        logger.error(f"Error adding item to cart: {str(e)}")
        return {
            "success": False,
            "message": f"Error adding item to cart: {str(e)}",
            "user_id": user_id,
            "cart_data": None
        }

@tool
def update_cart_item(user_id: str, cart_item_id: str, quantity: int = 1, to_be_deleted: bool = False) -> Dict[str, Any]:
    """
    Updates the quantity of an item in the user's cart or removes it completely.
    
    Args:
        user_id: The user ID
        cart_item_id: The cart item ID to update or remove
        quantity: The new quantity (ignored if to_be_deleted is True)
        to_be_deleted: If True, removes the item completely from cart
        
    Returns:
        Dict containing updated cart data and success status
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            return {
                "success": False,
                "message": "No user session found. Please log in to update your cart.",
                "user_id": None,
                "cart_data": None
            }
            
        if not cart_item_id:
            return {
                "success": False,
                "message": "Cart item ID is required to update cart item.",
                "user_id": user_id,
                "cart_data": None
            }
            
        # If item should be deleted, use DELETE endpoint
        if to_be_deleted:
            logger.info(f"Removing cart item for user: {user_id}, item: {cart_item_id}")
            
            url = f"{BACKEND_BASE_URL}/api/cart/user/{user_id}/items/{cart_item_id}"
            response = requests.delete(url, timeout=60)
            
            if response.status_code == 200:
                cart_data = response.json()
                logger.info(f"[SUCCESS] Successfully removed cart item for user: {user_id}")
                return {
                    "success": True,
                    "message": "Successfully removed item from your cart.",
                    "user_id": user_id,
                    "cart_data": cart_data
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": "Cart item not found or already removed.",
                    "user_id": user_id,
                    "cart_data": None
                }
            else:
                logger.warning(f"[ERROR] Remove cart item failed: {response.status_code}")
                return {
                    "success": False,
                    "message": "Failed to remove cart item. Please try again.",
                    "user_id": user_id,
                    "cart_data": None
                }
        
        # Otherwise update quantity
        if quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than 0. Set to_be_deleted=True to remove items.",
                "user_id": user_id,
                "cart_data": None
            }
            
        logger.info(f"Updating cart item for user: {user_id}, item: {cart_item_id}, quantity: {quantity}")
        
        # Call the simple backend cart endpoint (no JWT needed)
        url = f"{BACKEND_BASE_URL}/api/cart/user/{user_id}/items/{cart_item_id}"
        headers = {"Content-Type": "application/json"}
        data = {"quantity": quantity}
        
        response = requests.put(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            cart_data = response.json()
            logger.info(f"[SUCCESS] Successfully updated cart item for user: {user_id}")
            return {
                "success": True,
                "message": f"Successfully updated cart item quantity to {quantity}.",
                "user_id": user_id,
                "cart_data": cart_data
            }
        elif response.status_code == 404:
            return {
                "success": False,
                "message": "Cart item not found. It may have been removed already.",
                "user_id": user_id,                "cart_data": None
            }
        else:
            logger.warning(f"[ERROR] Update cart item failed: {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to update cart item. Please try again.",
                "user_id": user_id,
                "cart_data": None
            }
            
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating cart item: {str(e)}",
            "user_id": user_id,
            "cart_data": None
        }