import os
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env_variable(var_name):
    """Get an environment variable or raise an exception if it doesn't exist."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set")
    return value

def format_date_for_notion(date_obj):
    """Format a date object for Notion API."""
    from datetime import datetime
    
    # If it's already a string, try to parse it
    if isinstance(date_obj, str):
        try:
            # Try to parse the string as a datetime
            date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00'))
        except ValueError:
            # If it fails, try to parse as date only
            try:
                date_obj = datetime.strptime(date_obj, "%Y-%m-%d")
            except ValueError:
                # If all parsing fails, try natural language parsing
                date_obj = parse_natural_language_date(date_obj)
                # If it's still a string after natural language parsing, return it
                # (the API will handle the error)
                if isinstance(date_obj, str):
                    return date_obj
    
    if isinstance(date_obj, datetime):
        # Format as ISO 8601 string
        return date_obj.isoformat()
    
    # If it's neither a string nor a datetime, return as is
    return date_obj

def extract_notion_page_id(page_url):
    """Extract the Notion page ID from a URL or ID string."""
    # If it's already just an ID (32 chars with dashes), return it
    if re.match(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$', page_url):
        return page_url
    
    # Extract from URL format like https://www.notion.so/My-Store-1c814f08ff408033afa8dd9238d9f7d4
    match = re.search(r'([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$', page_url)
    if match:
        page_id = match.group(1)
        # If it's a 32-char ID without dashes, format it with dashes
        if len(page_id) == 32 and '-' not in page_id:
            return f"{page_id[0:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:32]}"
        return page_id
    
    raise ValueError(f"Could not extract Notion page ID from: {page_url}")

# Add this function to your utils.py file

def parse_date_string(date_str):
    """Parse a date string into a datetime object."""
    # Try to parse the string as a datetime
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except ValueError:
        # If it fails, try to parse as date only
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # If all parsing fails, raise ValueError
            raise ValueError(f"Could not parse date string: {date_str}")

def parse_natural_language_date(date_string):
    """
    Parse a natural language date string into a datetime object.
    Examples: "tomorrow", "next week", "in 3 days", etc.
    """
    from datetime import datetime, timedelta
    import re
    
    # Current date as reference point
    now = datetime.now()
    
    if not date_string or not isinstance(date_string, str):
        return None
        
    date_string = date_string.lower().strip()
    
    # Handle common natural language date expressions
    if date_string in ["today", "now"]:
        return now
    
    if date_string == "tomorrow":
        return now + timedelta(days=1)
    
    if date_string == "next week":
        return now + timedelta(weeks=1)
    
    # Handle "in X days/weeks/months"
    in_pattern = re.compile(r"in\s+(\d+)\s+(day|days|week|weeks|month|months)")
    match = in_pattern.match(date_string)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit in ["day", "days"]:
            return now + timedelta(days=amount)
        elif unit in ["week", "weeks"]:
            return now + timedelta(weeks=amount)
        elif unit in ["month", "months"]:
            # Approximate a month as 30 days
            return now + timedelta(days=30 * amount)
    
    # Handle "after X days/weeks/months"
    after_pattern = re.compile(r"after\s+(\d+)\s+(day|days|week|weeks|month|months)")
    match = after_pattern.match(date_string)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        
        if unit in ["day", "days"]:
            return now + timedelta(days=amount)
        elif unit in ["week", "weeks"]:
            return now + timedelta(weeks=amount)
        elif unit in ["month", "months"]:
            # Approximate a month as 30 days
            return now + timedelta(days=30 * amount)
    
    # Try standard date parsing as a fallback
    try:
        return parse_date_string(date_string)
    except:
        # If all parsing fails, return None
        return None