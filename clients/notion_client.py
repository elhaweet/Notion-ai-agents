import os
import json
import requests
from datetime import datetime
from utils.utils import get_env_variable, format_date_for_notion, extract_notion_page_id


class NotionClient:
    """Client for interacting with the Notion API."""
    
    def __init__(self):
        """Initialize the Notion client with API key and endpoint from environment variables."""
        self.api_key = get_env_variable("NOTION_API_KEY")
        self.endpoint = get_env_variable("NOTION_ENDPOINT")
        self.page_id = extract_notion_page_id(get_env_variable("NOTION_PAGE_ID"))
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"  # Use the latest version available
        }
    
    def _make_request(self, method, endpoint, data=None):
        """Make a request to the Notion API."""
        url = f"{self.endpoint}/{endpoint}"
        
        try:
            if method.lower() == "get":
                response = requests.get(url, headers=self.headers)
            elif method.lower() == "post":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.lower() == "patch":
                response = requests.patch(url, headers=self.headers, json=data)
            elif method.lower() == "delete":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to Notion API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            return None
    
    def get_database_id(self):
        """Get the database ID for the calendar database."""
        # First, get the page content to find the database
        response = self._make_request("get", f"blocks/{self.page_id}/children")
        
        if response and "results" in response:
            # Look for a database block
            for block in response["results"]:
                if block["type"] == "child_database":
                    return block["id"]
        
        # If no database found, create one
        return self.create_calendar_database()
    
    def create_calendar_database(self):
        """Create a new calendar database in the specified page."""
        data = {
            "parent": {"page_id": self.page_id},
            "title": [{"type": "text", "text": {"content": "Calendar Events"}}],
            "properties": {
                "Name": {"title": {}},
                "Date": {"date": {}},
                "End Date": {"date": {}},
                "Description": {"rich_text": {}},
                "Location": {"rich_text": {}},
                "Participants": {"rich_text": {}}
            }
        }
        
        response = self._make_request("post", "databases", data)
        if response and "id" in response:
            return response["id"]
        return None
    
    def get_calendar_events(self, start_date=None, end_date=None):
        """Get calendar events from the database."""
        database_id = self.get_database_id()
        if not database_id:
            return []
        
        # Build filter for date range if provided
        filter_data = {}
        if start_date or end_date:
            date_filter = {"property": "Date"}
            if start_date and end_date:
                date_filter["date"] = {
                    "on_or_after": format_date_for_notion(start_date),
                    "on_or_before": format_date_for_notion(end_date)
                }
            elif start_date:
                date_filter["date"] = {"on_or_after": format_date_for_notion(start_date)}
            elif end_date:
                date_filter["date"] = {"on_or_before": format_date_for_notion(end_date)}
            
            filter_data = {"filter": date_filter}
        
        # Query the database
        response = self._make_request("post", f"databases/{database_id}/query", filter_data)
        
        if response and "results" in response:
            # Process and return the events
            events = []
            for item in response["results"]:
                event = self._parse_event_from_response(item)
                if event:
                    events.append(event)
            return events
        
        return []
    
    def create_calendar_event(self, event_data):
        """Create a new calendar event."""
        database_id = self.get_database_id()
        if not database_id:
            return None
        
        # Prepare the properties for the new page
        properties = {
            "Name": {"title": [{"text": {"content": event_data.get("event_name", "Untitled Event")}}]},
            "Date": {"date": {"start": format_date_for_notion(event_data.get("start_date", datetime.now()))}}
        }
        
        # Add end date if provided
        if "end_date" in event_data and event_data["end_date"]:
            properties["End Date"] = {"date": {"start": format_date_for_notion(event_data["end_date"])}}
        
        # Add description if provided
        if "description" in event_data and event_data["description"]:
            properties["Description"] = {"rich_text": [{"text": {"content": event_data["description"]}}]}
        
        # Add location if provided
        if "location" in event_data and event_data["location"]:
            properties["Location"] = {"rich_text": [{"text": {"content": event_data["location"]}}]}
        
        # Add participants if provided
        if "participants" in event_data and event_data["participants"]:
            if isinstance(event_data["participants"], list):
                participants = ", ".join(event_data["participants"])
            else:
                participants = event_data["participants"]
            properties["Participants"] = {"rich_text": [{"text": {"content": participants}}]}
        
        # Create the page
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        response = self._make_request("post", "pages", data)
        if response and "id" in response:
            return {"id": response["id"], **self._parse_event_from_response(response)}
        
        return None
    
    def update_calendar_event(self, event_id, event_data):
        """Update an existing calendar event."""
        # Prepare the properties to update
        properties = {}
        
        if "event_name" in event_data:
            properties["Name"] = {"title": [{"text": {"content": event_data["event_name"]}}]}
        
        if "start_date" in event_data:
            properties["Date"] = {"date": {"start": format_date_for_notion(event_data["start_date"])}}
        
        if "end_date" in event_data:
            properties["End Date"] = {"date": {"start": format_date_for_notion(event_data["end_date"])}}
        
        if "description" in event_data:
            properties["Description"] = {"rich_text": [{"text": {"content": event_data["description"]}}]}
        
        if "location" in event_data:
            properties["Location"] = {"rich_text": [{"text": {"content": event_data["location"]}}]}
        
        if "participants" in event_data:
            if isinstance(event_data["participants"], list):
                participants = ", ".join(event_data["participants"])
            else:
                participants = event_data["participants"]
            properties["Participants"] = {"rich_text": [{"text": {"content": participants}}]}
        
        # Update the page
        data = {"properties": properties}
        response = self._make_request("patch", f"pages/{event_id}", data)
        
        if response and "id" in response:
            return {"id": response["id"], **self._parse_event_from_response(response)}
        
        return None
    
    def delete_calendar_event(self, event_id):
        """Delete (archive) a calendar event."""
        # In Notion, you can't actually delete pages, only archive them
        data = {"archived": True}
        response = self._make_request("patch", f"pages/{event_id}", data)
        
        if response and "id" in response and response.get("archived", False):
            return True
        
        return False
    
    def _parse_event_from_response(self, response):
        """Parse event data from a Notion API response."""
        if not response or "properties" not in response:
            return None
        
        properties = response["properties"]
        event = {"id": response["id"]}
        
        # Extract event name
        if "Name" in properties and properties["Name"]["title"]:
            title_items = properties["Name"]["title"]
            if title_items and "text" in title_items[0] and "content" in title_items[0]["text"]:
                event["event_name"] = title_items[0]["text"]["content"]
        
        # Extract start date
        if "Date" in properties and properties["Date"]["date"]:
            date_obj = properties["Date"]["date"]
            if "start" in date_obj:
                event["start_date"] = date_obj["start"]
        
        # Extract end date
        if "End Date" in properties and properties["End Date"]["date"]:
            date_obj = properties["End Date"]["date"]
            if "start" in date_obj:
                event["end_date"] = date_obj["start"]
        
        # Extract description
        if "Description" in properties and properties["Description"]["rich_text"]:
            rich_text = properties["Description"]["rich_text"]
            if rich_text and "text" in rich_text[0] and "content" in rich_text[0]["text"]:
                event["description"] = rich_text[0]["text"]["content"]
        
        # Extract location
        if "Location" in properties and properties["Location"]["rich_text"]:
            rich_text = properties["Location"]["rich_text"]
            if rich_text and "text" in rich_text[0] and "content" in rich_text[0]["text"]:
                event["location"] = rich_text[0]["text"]["content"]
        
        # Extract participants
        if "Participants" in properties and properties["Participants"]["rich_text"]:
            rich_text = properties["Participants"]["rich_text"]
            if rich_text and "text" in rich_text[0] and "content" in rich_text[0]["text"]:
                event["participants"] = rich_text[0]["text"]["content"]
        
        return event
    
    # Add these methods to your existing NotionClient class
    
    def get_todo_database_id(self):
        """Get the database ID for the todo database."""
        # First, get the page content to find the database
        response = self._make_request("get", f"blocks/{self.page_id}/children")
        
        if response and "results" in response:
            # Look for a database block with "Todo" in the title
            for block in response["results"]:
                if block["type"] == "child_database":
                    # Try to get the title to check if it's a todo database
                    db_id = block["id"]
                    db_info = self._make_request("get", f"databases/{db_id}")
                    if db_info and "title" in db_info:
                        title = ""
                        for title_part in db_info["title"]:
                            if "text" in title_part and "content" in title_part["text"]:
                                title += title_part["text"]["content"]
                        if "todo" in title.lower() or "task" in title.lower():
                            return db_id
    
        # If no database found, create one
        return self.create_todo_database()
    
    def create_todo_database(self):
        """Create a new todo database in the specified page."""
        data = {
            "parent": {"page_id": self.page_id},
            "title": [{"type": "text", "text": {"content": "Todo Items"}}],
            "properties": {
                "Task": {"title": {}},
                "Due Date": {"date": {}},
                "Status": {"select": {
                    "options": [
                        {"name": "Not Started", "color": "gray"},
                        {"name": "In Progress", "color": "blue"},
                        {"name": "Completed", "color": "green"}
                    ]
                }},
                "Priority": {"select": {
                    "options": [
                        {"name": "Low", "color": "gray"},
                        {"name": "Medium", "color": "yellow"},
                        {"name": "High", "color": "red"}
                    ]
                }},
                "Notes": {"rich_text": {}}
            }
        }
        
        response = self._make_request("post", "databases", data)
        if response and "id" in response:
            return response["id"]
        return None
    
    def get_todo_items(self, filter_info=None):
        """Get todo items from the database."""
        database_id = self.get_todo_database_id()
        if not database_id:
            return []
        
        # Build filter if provided
        filter_data = {}
        if filter_info:
            # Example: Filter by status
            if "status" in filter_info:
                filter_data = {
                    "filter": {
                        "property": "Status",
                        "select": {
                            "equals": filter_info["status"]
                        }
                    }
                }
            # Example: Filter by due date
            elif "due_date" in filter_info:
                filter_data = {
                    "filter": {
                        "property": "Due Date",
                        "date": {
                            "on_or_before": format_date_for_notion(filter_info["due_date"])
                        }
                    }
                }
        
        # Query the database
        response = self._make_request("post", f"databases/{database_id}/query", filter_data)
        
        if response and "results" in response:
            # Process and return the todos
            todos = []
            for item in response["results"]:
                todo = self._parse_todo_from_response(item)
                if todo:
                    todos.append(todo)
            return todos
        
        return []
    
    def create_todo_item(self, todo_data):
        """Create a new todo item."""
        database_id = self.get_todo_database_id()
        if not database_id:
            return None
        
        # Prepare the properties for the new page
        properties = {
            "Task": {"title": [{"text": {"content": todo_data.get("task_name", "Untitled Task")}}]}
        }
        
        # Add due date if provided
        if "due_date" in todo_data and todo_data["due_date"]:
            properties["Due Date"] = {"date": {"start": format_date_for_notion(todo_data["due_date"])}}
        
        # Add status if provided
        if "status" in todo_data and todo_data["status"]:
            properties["Status"] = {"select": {"name": todo_data["status"]}}
        
        # Add priority if provided
        if "priority" in todo_data and todo_data["priority"]:
            properties["Priority"] = {"select": {"name": todo_data["priority"]}}
        
        # Add notes if provided
        if "notes" in todo_data and todo_data["notes"]:
            properties["Notes"] = {"rich_text": [{"text": {"content": todo_data["notes"]}}]}
        
        # Create the page
        data = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        response = self._make_request("post", "pages", data)
        if response and "id" in response:
            return {"id": response["id"], **self._parse_todo_from_response(response)}
        
        return None
    
    def update_todo_item(self, todo_id, todo_data):
        """Update an existing todo item."""
        # Prepare the properties to update
        properties = {}
        
        if "task_name" in todo_data:
            properties["Task"] = {"title": [{"text": {"content": todo_data["task_name"]}}]}
        
        if "due_date" in todo_data:
            properties["Due Date"] = {"date": {"start": format_date_for_notion(todo_data["due_date"])}}
        
        # Only include Status if it has a valid value
        if "status" in todo_data and todo_data["status"]:
            properties["Status"] = {"select": {"name": todo_data["status"]}}
        
        if "priority" in todo_data:
            properties["Priority"] = {"select": {"name": todo_data["priority"]}}
        
        if "notes" in todo_data:
            properties["Notes"] = {"rich_text": [{"text": {"content": todo_data["notes"]}}]}
        
        # Update the page
        data = {"properties": properties}
        response = self._make_request("patch", f"pages/{todo_id}", data)
        
        if response and "id" in response:
            return {"id": response["id"], **self._parse_todo_from_response(response)}
        
        return None
    
    def delete_todo_item(self, todo_id):
        """Delete (archive) a todo item."""
        # In Notion, you can't actually delete pages, only archive them
        data = {"archived": True}
        response = self._make_request("patch", f"pages/{todo_id}", data)
        
        if response and "id" in response and response.get("archived", False):
            return True
        
        return False
    
    def _parse_todo_from_response(self, response):
        """Parse todo data from a Notion API response."""
        if not response or "properties" not in response:
            return None
        
        properties = response["properties"]
        todo = {"id": response["id"]}
        
        # Extract task name
        if "Task" in properties and properties["Task"]["title"]:
            title_items = properties["Task"]["title"]
            if title_items and "text" in title_items[0] and "content" in title_items[0]["text"]:
                todo["task_name"] = title_items[0]["text"]["content"]
        
        # Extract due date
        if "Due Date" in properties and properties["Due Date"]["date"]:
            date_obj = properties["Due Date"]["date"]
            if "start" in date_obj:
                todo["due_date"] = date_obj["start"]
        
        # Extract status
        if "Status" in properties and properties["Status"]["select"]:
            select_obj = properties["Status"]["select"]
            if select_obj and "name" in select_obj:
                todo["status"] = select_obj["name"]
        
        # Extract priority
        if "Priority" in properties and properties["Priority"]["select"]:
            select_obj = properties["Priority"]["select"]
            if select_obj and "name" in select_obj:
                todo["priority"] = select_obj["name"]
        
        # Extract notes
        if "Notes" in properties and properties["Notes"]["rich_text"]:
            rich_text = properties["Notes"]["rich_text"]
            if rich_text and "text" in rich_text[0] and "content" in rich_text[0]["text"]:
                todo["notes"] = rich_text[0]["text"]["content"]
        
        return todo