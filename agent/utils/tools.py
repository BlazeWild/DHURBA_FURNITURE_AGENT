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
def validate_user_authentication(user_id: str) -> Dict[str, Any]:
    """
    Validates if a user is authenticated and has a valid session.
    
    The LLM should call this tool when:
    - User asks about their login status
    - User wants to check if they're logged in
    - Need to verify authentication before accessing protected resources
    
    Args:
        user_id: The user ID to validate
        
    Returns:
        Dict containing authentication status and user information
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.info("No user ID provided for authentication validation")
            return {
                "success": False,
                "authenticated": False,
                "message": "No user session found. Please log in.",
                "user_id": None
            }
        
        logger.info(f"Validating authentication for user: {user_id}")
        # Call backend auth validation endpoint
        url = f"{BACKEND_BASE_URL}/api/auth/validate-user/{user_id}"
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            auth_data = response.json()
            logger.info(f"[SUCCESS] User {user_id} is authenticated")
            return {
                "success": True,
                "authenticated": True,
                "message": "User is authenticated and session is active",
                "user_id": user_id,
                "auth_data": auth_data
            }
        elif response.status_code == 401:
            logger.info(f"[ERROR] User {user_id} authentication failed")
            return {
                "success": True,
                "authenticated": False,
                "message": "User session is invalid or expired. Please log in again.",
                "user_id": user_id,
                "auth_data": None
            }
        else:
            logger.warning(f"[ERROR] Auth validation failed: {response.status_code}")
            return {
                "success": False,
                "authenticated": False,
                "message": "Authentication validation failed. Please try again.",
                "user_id": user_id,
                "auth_data": None
            }
            
    except Exception as e:
        logger.error(f"Error validating user authentication: {str(e)}")
        return {
            "success": False,
            "authenticated": False,
            "message": f"Error validating authentication: {str(e)}",
            "user_id": user_id,
            "auth_data": None
        }


@tool
def get_user_profile_data(user_id: str) -> Dict[str, Any]:
    """
    Fetches user profile data for authenticated users.
    
    The LLM should call this tool when:
    - User asks for profile information of name, address, phone number email, and not more than that
    - User requests account details
    - User wants to see their personal information
    
    Args:
        user_id: The user ID to fetch profile data for
        
    Returns:
        Dict containing profile data and success status
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.info("No user ID provided for profile data fetch")
            return {
                "success": False,
                "message": "No user session found. Please log in to view your profile.",
                "user_id": None,
                "profile_data": None
            }
            
        logger.info(f"Fetching profile data for user: {user_id}")
        # Call backend profile endpoint
        # Increased timeout to handle circular request pattern (backend -> MCP -> backend)
        url = f"{BACKEND_BASE_URL}/api/profile/user/{user_id}"
        response = requests.get(url, timeout=60)  # Increased from 10 to 60 seconds
        
        if response.status_code == 200:
            profile_data = response.json()
            logger.info(f"[SUCCESS] Successfully retrieved profile for user: {user_id}")
            return {
                "success": True,
                "message": "Profile data retrieved successfully",
                "user_id": user_id,
                "profile_data": profile_data
            }
        elif response.status_code == 404:
            logger.info(f"[ERROR] Profile not found for user: {user_id}")
            return {
                "success": False,
                "message": "Profile not found. Please complete your profile setup through the frontend.",
                "user_id": user_id,
                "profile_data": None
            }
        else:
            logger.warning(f"[ERROR] Profile fetch failed: {response.status_code}")
            return {
                "success": False,
                "message": f"Failed to retrieve profile data. Please try again or contact support.",
                "user_id": user_id,
                "profile_data": None
            }
            
    except Exception as e:
        logger.error(f"Error fetching user profile: {str(e)}")
        return {
            "success": False,
            "message": f"Error retrieving profile: {str(e)}",
            "user_id": user_id,
            "profile_data": None
        }



# @tool
# def get_furniture_establishment(query: str) -> Dict:
#     """
#     Get establishment information for the dhurba furniture store.

#     Args:
#         query (str): Additional query input (can be used for natural language prompts).

#     Returns:
#         Dict: Dictionary containing establishment information for the furniture store.
#     """
#     try:
#         establishment_info = {
#             "establishment_date": "2010-10-01",
#             "founder": "Dhurba BK",
#             "store_name": "Dhurba Furniture Store",
#             "success": True
#         }
#         return establishment_info
#     except Exception as e:
#         logger.error(f"Error fetching furniture establishment information: {str(e)}")
#         return {
#             "success": False,
#             "error": str(e)
#         }

@tool
def update_user_profile(user_id: str, first_name: str = None, last_name: str = None, address: str = None) -> Dict[str, Any]:
    """
    Updates user profile data for authenticated users. Only first name, last name, and address can be modified.
    
    The LLM should call this tool when:
    - User asks to update their name ("Change my name to John Doe", "Update my first name", etc.)
    - User asks to update their address ("Change my address to...", "Update my location", etc.)
    - User wants to modify their personal information (limited to name and address only)
    
    Important restrictions:
    - Email cannot be changed through this tool
    - Phone number cannot be changed through this tool  
    - Profile picture must be updated manually through the frontend
    
    The LLM should intelligently parse user requests to distinguish between first name and last name.
    
    Args:
        user_id: The user ID for the authenticated user
        first_name: New first name (optional)
        last_name: New last name (optional)  
        address: New address (optional)
        
    Returns:
        Dict containing update status and result
    """
    try:
        if not user_id or user_id == "null" or user_id == "undefined":
            logger.info("No user ID provided for profile update")
            return {
                "success": False,
                "message": "No user session found. Please log in to update your profile.",
                "user_id": None
            }
        
        # Check if any valid updates were provided
        updates_to_make = {}
        if first_name is not None and first_name.strip():
            updates_to_make["first_name"] = first_name.strip()
        if last_name is not None and last_name.strip():
            updates_to_make["last_name"] = last_name.strip()
        if address is not None and address.strip():
            updates_to_make["address"] = address.strip()
            
        if not updates_to_make:
            logger.info(f"No valid updates provided for user: {user_id}")
            return {
                "success": True,
                "message": "No updates to be made. Your profile remains unchanged.",
                "user_id": user_id,
                "updates_made": {}
            }
        logger.info(f"Updating profile for user: {user_id} with updates: {list(updates_to_make.keys())}")
        
        # Call backend profile update endpoint using the MCP-compatible endpoint
        url = f"{BACKEND_BASE_URL}/api/profile/user/{user_id}/update"
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.patch(url, json=updates_to_make, headers=headers, timeout=60)
        
        if response.status_code == 200:
            updated_data = response.json()
            logger.info(f"[SUCCESS] Profile updated successfully for user: {user_id}")
            
            # Create a friendly response about what was updated
            updated_fields = []
            if "first_name" in updates_to_make:
                updated_fields.append(f"first name to '{updates_to_make['first_name']}'")
            if "last_name" in updates_to_make:
                updated_fields.append(f"last name to '{updates_to_make['last_name']}'")
            if "address" in updates_to_make:
                updated_fields.append(f"address to '{updates_to_make['address']}'")
                
            update_message = f"Successfully updated your {', '.join(updated_fields)}."
            
            return {
                "success": True,
                "message": update_message,
                "user_id": user_id,
                "updates_made": updates_to_make,
                "profile_data": updated_data
            }
        elif response.status_code == 404:
            logger.warning(f"[ERROR] Profile not found for user: {user_id}")
            return {
                "success": False,
                "message": "Profile not found. Please complete your profile setup through the profile settings page first.",
                "user_id": user_id,
                "updates_made": {}
            }
        elif response.status_code == 401:
            logger.warning(f"[ERROR] Unauthorized access for user: {user_id}")
            return {
                "success": False,
                "message": "Authentication failed. Please log in again to update your profile.",
                "user_id": user_id,
                "updates_made": {}
            }
        else:
            logger.warning(f"[ERROR] Profile update failed: {response.status_code} - {response.text}")
            return {
                "success": False,
                "message": f"Failed to update profile. Please try again or contact support.",
                "user_id": user_id,
                "updates_made": {}
            }
            
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating profile: {str(e)}",
            "user_id": user_id,
            "updates_made": {}
        }
