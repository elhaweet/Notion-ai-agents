from datetime import datetime, timedelta
import re
import dateparser

def parse_date_string(date_string):
    """
    Parse a date string in various formats and return a datetime object.
    
    Args:
        date_string (str): A string representing a date
        
    Returns:
        datetime or str: A datetime object representing the parsed date or ISO format string
    """
    if not date_string:
        return None
        
    # Try to parse with dateparser which handles many formats
    parsed_date = dateparser.parse(date_string)
    
    if parsed_date:
        # Return ISO format string for Notion API
        return parsed_date.isoformat()
    
    # Handle relative dates
    if isinstance(date_string, str):
        if "tomorrow" in date_string.lower():
            return (datetime.now() + timedelta(days=1)).isoformat()
        elif "today" in date_string.lower():
            return datetime.now().isoformat()
        elif "next week" in date_string.lower():
            return (datetime.now() + timedelta(days=7)).isoformat()
        elif "two days" in date_string.lower() or "2 days" in date_string.lower():
            return (datetime.now() + timedelta(days=2)).isoformat()
        elif "three days" in date_string.lower() or "3 days" in date_string.lower():
            return (datetime.now() + timedelta(days=3)).isoformat()
    
    # If all parsing fails, return None
    return None

def parse_natural_language_date(text):
    """
    Extract and parse dates from natural language text.
    
    Args:
        text (str): Natural language text containing date references
        
    Returns:
        str: ISO formatted date string for Notion API
    """
    if not text:
        return None
        
    # Try direct parsing first
    parsed_date = parse_date_string(text)
    if parsed_date:
        return parsed_date
    
    # Check for common date patterns
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Handle "today", "tomorrow", "next week", etc.
    if re.search(r'\btoday\b', text, re.IGNORECASE):
        return today.isoformat()
    elif re.search(r'\btomorrow\b', text, re.IGNORECASE):
        return (today + timedelta(days=1)).isoformat()
    elif re.search(r'\bnext week\b', text, re.IGNORECASE):
        return (today + timedelta(days=7)).isoformat()
    elif re.search(r'\btwo days?\b|in 2 days?\b', text, re.IGNORECASE):
        return (today + timedelta(days=2)).isoformat()
    elif re.search(r'\bthree days?\b|in 3 days?\b', text, re.IGNORECASE):
        return (today + timedelta(days=3)).isoformat()
    
    # Try to extract specific dates using dateparser
    date_matches = re.findall(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2} [A-Za-z]+ \d{2,4}|[A-Za-z]+ \d{1,2}(?:st|nd|rd|th)? \d{2,4})\b', text)
    
    if date_matches:
        for date_str in date_matches:
            parsed_date = parse_date_string(date_str)
            if parsed_date:
                return parsed_date
    
    # Default to tomorrow if we can't parse a specific date
    return (today + timedelta(days=1)).isoformat()