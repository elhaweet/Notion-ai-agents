
from clients.notion_client import NotionClient
from clients.gemini_client import GeminiClient
from utils import utils
from utils.date_parser import parse_date_string, parse_natural_language_date
from datetime import datetime, timedelta

class TodoAgent:
    """Agent for managing todo items in Notion with AI capabilities."""
    
    def __init__(self, memory_manager=None):
        """Initialize the todo agent with Notion and Gemini clients."""
        self.notion_client = NotionClient()
        self.gemini_client = GeminiClient(memory_manager=memory_manager)
        self.memory_manager = memory_manager
    
    def process_request(self, user_input):
        """Process a natural language request from the user."""
        # Get current todos for context
        current_todos = self.notion_client.get_todo_items()
        
        # Use Gemini to suggest what action to take
        action_suggestion = self.gemini_client.suggest_todo_actions(user_input, current_todos)
        
        # Handle case where action_suggestion might be a list or other non-dictionary type
        if not isinstance(action_suggestion, dict):
            print(f"Warning: Received unexpected response type: {type(action_suggestion)}")
            action_suggestion = {"action": "unknown"}
        
        action = action_suggestion.get("action", "unknown")
        
        if action == "create":
            return self.create_todo_from_text(user_input)
        elif action == "read":
            return self.read_todos_from_text(user_input)
        elif action == "update":
            todo_id = action_suggestion.get("todo_id")
            return self.update_todo_from_text(user_input, todo_id)
        elif action == "delete":
            todo_id = action_suggestion.get("todo_id")
            return self.delete_todo_from_text(user_input, todo_id)
        else:
            return {"status": "error", "message": "I'm not sure what you want to do with your todo list."}
    
    ## 2. Now, let's update the TodoAgent's create_todo_from_text method:
    def create_todo_from_text(self, text):
        """Create a new todo item from natural language text."""
        # Extract todo information from text
        todo_data = self.gemini_client.process_natural_language(text)
        
        if not todo_data or "task_name" not in todo_data:
            return {
                "status": "error", 
                "message": "I couldn't extract enough information to create a todo item. Please provide at least a task name."
            }
        
        # Process natural language dates if present
        if "due_date" in todo_data:
            try:
                # Try to convert natural language date to ISO string
                from utils.date_parser import parse_natural_language_date
                parsed_date = parse_natural_language_date(todo_data["due_date"])
                if parsed_date:
                    todo_data["due_date"] = parsed_date
                else:
                    # If date parsing fails, set to tomorrow
                    todo_data["due_date"] = (datetime.now() + timedelta(days=1)).isoformat()
            except Exception as e:
                print(f"Error parsing date: {str(e)}")
                # If date parsing fails, set to tomorrow
                todo_data["due_date"] = (datetime.now() + timedelta(days=1)).isoformat()
        else:
            # Default due date to tomorrow if not specified
            todo_data["due_date"] = (datetime.now() + timedelta(days=1)).isoformat()
        
        # Create the todo in Notion
        result = self.notion_client.create_todo_item(todo_data)
        
        if result:
            due_date_str = ""
            if "due_date" in result and result["due_date"]:
                due_date_str = f" with due date {result['due_date']}"
            else:
                due_date_str = " with no due date"
                
            return {
                "status": "success",
                "message": f"Created todo '{result.get('task_name', 'Untitled')}'{due_date_str}",
                "todo": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to create the todo item in Notion."
            }
    
    def read_todos_from_text(self, text):
        """Read todo items based on natural language text."""
        # Extract filter information from text
        filter_info = self.gemini_client.process_natural_language(text)
        
        # Process date filters if they exist
        if "due_date" in filter_info and filter_info["due_date"]:
            try:
                if isinstance(filter_info["due_date"], str):
                    filter_info["due_date"] = parse_natural_language_date(filter_info["due_date"])
            except ValueError:
                # Remove invalid date filter
                del filter_info["due_date"]
        
        # Get todos from Notion
        todos = self.notion_client.get_todo_items(filter_info)
        
        if todos:
            # Generate a summary of the todos
            summary = self.gemini_client.generate_todo_summary(todos)
            return {
                "status": "success",
                "message": summary,
                "todos": todos
            }
        else:
            return {
                "status": "success",
                "message": "No todo items found matching your criteria.",
                "todos": []
            }
    
    def update_todo_from_text(self, text, todo_id=None):
        """Update an existing todo item from natural language text."""
        # If no todo_id provided, try to identify the todo from the text
        if not todo_id:
            # Get recent todos to compare with
            todos = self.notion_client.get_todo_items()
            
            # Use Gemini to try to identify which todo to update
            todo_data = self.gemini_client.process_natural_language(text)
            
            # Try to match by name using fuzzy matching
            if todos and "task_name" in todo_data:
                task_name_lower = todo_data["task_name"].lower()
                
                # First try exact match
                for todo in todos:
                    if todo.get("task_name", "").lower() == task_name_lower:
                        todo_id = todo["id"]
                        break
                
                # If no exact match, try partial match
                if not todo_id:
                    for todo in todos:
                        todo_name_lower = todo.get("task_name", "").lower()
                        # Check if the task name contains the search term or vice versa
                        if task_name_lower in todo_name_lower or todo_name_lower in task_name_lower:
                            todo_id = todo["id"]
                            break
            
            # If still no match and "status" indicates completion, try to find incomplete tasks
            if not todo_id and todo_data.get("status", "").lower() in ["done", "completed", "complete"]:
                for todo in todos:
                    if todo.get("status", "").lower() not in ["done", "completed", "complete"]:
                        # This is a potential candidate for marking as done
                        todo_id = todo["id"]
                        break
        
        if not todo_id:
            return {
                "status": "error",
                "message": "I couldn't identify which todo item you want to update. Please specify the task name more clearly."
            }
        
        # Extract update information from text
        update_data = self.gemini_client.process_natural_language(text)
        
        if not update_data:
            return {
                "status": "error",
                "message": "I couldn't extract any information to update the todo item. Please specify what you want to change."
            }
        
        # Update the todo in Notion
        result = self.notion_client.update_todo_item(todo_id, update_data)
        
        if result:
            return {
                "status": "success",
                "message": f"Updated todo '{result.get('task_name', 'Untitled')}'",
                "todo": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to update the todo item in Notion."
            }
    
    def delete_todo_from_text(self, text, todo_id=None):
        """Delete a todo item based on natural language text."""
        # If no todo_id provided, try to identify the todo from the text
        if not todo_id:
            # Get recent todos to compare with
            todos = self.notion_client.get_todo_items()
            
            # Use Gemini to try to identify which todo to delete
            todo_data = self.gemini_client.process_natural_language(text)
            
            # Try to match by name using fuzzy matching
            if todos and "task_name" in todo_data:
                task_name_lower = todo_data["task_name"].lower()
                
                # First try exact match
                for todo in todos:
                    if todo.get("task_name", "").lower() == task_name_lower:
                        todo_id = todo["id"]
                        break
                
                # If no exact match, try partial match
                if not todo_id:
                    for todo in todos:
                        todo_name_lower = todo.get("task_name", "").lower()
                        # Check if the task name contains the search term or vice versa
                        if task_name_lower in todo_name_lower or todo_name_lower in task_name_lower:
                            todo_id = todo["id"]
                            break
            
            # If still no match and "status" indicates completion, try to find incomplete tasks
            if not todo_id and todo_data.get("status", "").lower() in ["done", "completed", "complete"]:
                for todo in todos:
                    if todo.get("status", "").lower() not in ["done", "completed", "complete"]:
                        # This is a potential candidate for marking as done
                        todo_id = todo["id"]
                        break
        
        if not todo_id:
            return {
                "status": "error",
                "message": "I couldn't identify which todo item you want to delete. Please specify the task name more clearly."
            }
        
        # Delete the todo in Notion
        result = self.notion_client.delete_todo_item(todo_id)
        
        if result:
            return {
                "status": "success",
                "message": "Todo item deleted successfully."
            }
        else:
            return {
                "status": "error",
                "message": "Failed to delete the todo item in Notion."
            }

    def mark_todo_as_done(self, text):
        """Mark a todo item as done based on natural language text."""
        # Get recent todos to compare with
        todos = self.notion_client.get_todo_items()
        
        # Use Gemini to try to identify which todo to mark as done
        todo_data = self.gemini_client.process_natural_language(text)
        
        todo_id = None
        # Try to match by name
        if todos and "task_name" in todo_data:
            print(f"Looking for task: '{todo_data['task_name']}'")
            for todo in todos:
                if "task_name" in todo and todo_data["task_name"].lower() in todo["task_name"].lower():
                    todo_id = todo["id"]
                    print(f"Found matching task: '{todo['task_name']}' with ID: {todo_id}")
                    break
        
        if not todo_id:
            return {
                "status": "error",
                "message": "I couldn't identify which todo item you want to mark as done. Please specify the task name more clearly."
            }
        
        # Update the todo status to "Completed"
        update_data = {"status": "Completed"}
        result = self.notion_client.update_todo_item(todo_id, update_data)
        
        if result:
            return {
                "status": "success",
                "message": f"Marked todo '{result.get('task_name', 'Untitled')}' as completed",
                "todo": result
            }
        else:
            return {
                "status": "error",
                "message": "Failed to update the todo item in Notion."
            }