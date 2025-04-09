from datetime import datetime, timedelta
from clients.notion_client import NotionClient
from clients.gemini_client import GeminiClient
from utils.utils import parse_date_string, parse_natural_language_date

class CalendarAgent:
    """Agent for managing calendar events in Notion with AI capabilities."""
    
    def __init__(self, memory_manager=None):
        """Initialize the calendar agent with Notion and Gemini clients."""
        self.notion_client = NotionClient()
        self.gemini_client = GeminiClient(memory_manager=memory_manager)
        self.memory_manager = memory_manager
    
    def process_request(self, user_input):
        """Process a natural language request from the user."""
        # Get current events for context
        current_events = self.notion_client.get_calendar_events()
        
        # Use Gemini to suggest what action to take
        action_suggestion = self.gemini_client.suggest_calendar_actions(user_input, current_events)
        
        # Handle case where action_suggestion might be a list or other non-dictionary type
        if not isinstance(action_suggestion, dict):
            print(f"Warning: Received unexpected response type: {type(action_suggestion)}")
            action_suggestion = {"action": "unknown"}
        
        action = action_suggestion.get("action", "unknown")
        
        if action == "create":
            return self.create_event_from_text(user_input)
        elif action == "read":
            return self.read_events_from_text(user_input)
        elif action == "update":
            event_id = action_suggestion.get("event_id")
            return self.update_event_from_text(user_input, event_id)
        elif action == "delete":
            event_id = action_suggestion.get("event_id")
            return self.delete_event_from_text(user_input, event_id)
        else:
            return {"status": "error", "message": "I'm not sure what you want to do with your calendar."}
    
    def create_event_from_text(self, text):
        """Create a new calendar event from natural language text."""
        # Extract event information from text
        event_data = self.gemini_client.process_natural_language(text)
        
        if not event_data or "event_name" not in event_data:
            return {
                "status": "error", 
                "message": "I couldn't extract enough information to create an event. Please provide at least an event name and date."
            }
        
        # Process natural language dates if present
        if "start_date" in event_data:
            try:
                # Try to convert natural language date to ISO string
                from utils.date_parser import parse_natural_language_date
                parsed_date = parse_natural_language_date(event_data["start_date"])
                if parsed_date:
                    event_data["start_date"] = parsed_date
                else:
                    # If date parsing fails, set to tomorrow
                    event_data["start_date"] = (datetime.now() + timedelta(days=1)).isoformat()
            except Exception as e:
                print(f"Error parsing date: {str(e)}")
                # If date parsing fails, set to tomorrow
                event_data["start_date"] = (datetime.now() + timedelta(days=1)).isoformat()
        else:
            # Default start date to tomorrow if not specified
            event_data["start_date"] = (datetime.now() + timedelta(days=1)).isoformat()
        
        # Create the event in Notion
        result = self.notion_client.create_calendar_event(event_data)
        
        if result:
            return {
                "status": "success",
                "message": f"Created event '{result.get('event_name', 'Untitled')}' on {result.get('start_date', 'unknown date')}",
                "event": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create the event in Notion."
            }
    
    def read_events_from_text(self, text):
        """Read calendar events based on natural language text."""
        # Extract date information from text
        date_info = self.gemini_client.process_natural_language(text)
        
        start_date = None
        end_date = None
        
        if "start_date" in date_info:
            try:
                start_date = parse_natural_language_date(date_info["start_date"])
            except ValueError:
                pass
        
        if "end_date" in date_info:
            try:
                end_date = parse_natural_language_date(date_info["end_date"])
            except ValueError:
                pass
        
        # If no dates specified, default to current week
        if not start_date and not end_date:
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week
            end_date = end_of_week
        
        # Get events from Notion
        events = self.notion_client.get_calendar_events(start_date, end_date)
        
        if events:
            # Generate a summary of the events
            summary = self.gemini_client.generate_event_summary(events)
            return {
                "status": "success",
                "message": summary,
                "events": events
            }
        else:
            time_range = ""
            if start_date and end_date:
                time_range = f" between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}"
            elif start_date:
                time_range = f" after {start_date.strftime('%Y-%m-%d')}"
            elif end_date:
                time_range = f" before {end_date.strftime('%Y-%m-%d')}"
                
            return {
                "status": "success",
                "message": f"No events found{time_range}.",
                "events": []
            }
    
    def update_event_from_text(self, text, event_id=None):
        """Update an existing calendar event based on natural language text."""
        # Get current events for context
        current_events = self.notion_client.get_calendar_events()
        
        # Extract event information from text
        update_data = self.gemini_client.process_natural_language(text)
        
        # If no event_id provided, try to find the event based on name or description
        if not event_id:
            event_keywords = ['software event', 'software', 'tech world']
            matching_events = []
            
            for event in current_events:
                event_name = event.get('event_name', '').lower()
                for keyword in event_keywords:
                    if keyword in text.lower() and keyword in event_name:
                        matching_events.append(event)
                        break
            
            if len(matching_events) == 1:
                event_id = matching_events[0].get('id')
                # Update the event data with existing values
                update_data = {
                    **matching_events[0],  # Keep existing data
                    **update_data,  # Override with new data
                }
            elif len(matching_events) > 1:
                return {
                    "status": "error",
                    "message": "Multiple matching events found. Please specify which event you want to update."
                }
        
        if not event_id:
            return {
                "status": "error",
                "message": "I couldn't identify which event you want to update. Please specify the event name or date more clearly."
            }
        
        # Handle priority updates
        if 'priority' in text.lower() or 'important' in text.lower():
            update_data['priority'] = 'High'
        
        # Update the event in Notion
        result = self.notion_client.update_calendar_event(event_id, update_data)
        
        if result:
            return {
                "status": "success",
                "message": f"Updated event '{result.get('event_name', 'Untitled')}' with new details",
                "event": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to update the event in Notion."
            }
    
    def delete_event_from_text(self, text, event_id=None):
        """Delete a calendar event based on natural language text."""
        # If no event_id provided, try to identify the event from the text
        if not event_id:
            # Get recent events to compare with
            events = self.notion_client.get_calendar_events()
            
            # Use Gemini to try to identify which event to delete
            event_data = self.gemini_client.process_natural_language(text)
            
            # Try to match by name or date
            if events and ("event_name" in event_data or "start_date" in event_data):
                for event in events:
                    if ("event_name" in event_data and 
                        event.get("event_name", "").lower() == event_data["event_name"].lower()):
                        event_id = event["id"]
                        break
                    elif ("start_date" in event_data and 
                          "start_date" in event and 
                          event["start_date"] == event_data["start_date"]):
                        event_id = event["id"]
                        break
        
        if not event_id:
            return {
                "status": "error",
                "message": "I couldn't identify which event you want to delete. Please specify the event name or date more clearly."
            }
        
        # Delete the event in Notion
        result = self.notion_client.delete_calendar_event(event_id)
        
        if result:
            return {
                "status": "success",
                "message": "Event deleted successfully."
            }
        else:
            return {
                "status": "error",
                "message": "Failed to delete the event in Notion."
            }