import os
import google.generativeai as genai
from datetime import datetime, timedelta
import re
import logging
from utils.utils import get_env_variable, parse_natural_language_date

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiClient:
    """Client for interacting with the Google Gemini API."""
    
    def __init__(self, memory_manager=None):
        """Initialize the Gemini client with API key from environment variables."""
        self.api_key = get_env_variable("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Add memory manager
        self.memory_manager = memory_manager
    
    def normalize_relative_dates(self, user_input):
        """Pre-process user input to normalize relative date expressions.
        
        Args:
            user_input (str): The original user input text
            
        Returns:
            str: User input with normalized date references
        """
        today = datetime.now()
        
        # Define patterns for relative date expressions
        patterns = [
            (r"after (\d+) days?", lambda m: (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")),
            (r"in (\d+) days?", lambda m: (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")),
            (r"(\d+) days? from now", lambda m: (today + timedelta(days=int(m.group(1)))).strftime("%Y-%m-%d")),
            (r"after a day", lambda m: (today + timedelta(days=1)).strftime("%Y-%m-%d")),
            (r"after a week", lambda m: (today + timedelta(days=7)).strftime("%Y-%m-%d")),
            (r"in a week", lambda m: (today + timedelta(days=7)).strftime("%Y-%m-%d")),
            (r"a week from now", lambda m: (today + timedelta(days=7)).strftime("%Y-%m-%d")),
            (r"a couple of days from now", lambda m: (today + timedelta(days=2)).strftime("%Y-%m-%d")),
            (r"in a couple of days", lambda m: (today + timedelta(days=2)).strftime("%Y-%m-%d")),
            (r"in a few days", lambda m: (today + timedelta(days=3)).strftime("%Y-%m-%d")),
            (r"after a few days", lambda m: (today + timedelta(days=3)).strftime("%Y-%m-%d")),
        ]
        
        # Apply all patterns
        normalized_input = user_input
        for pattern, replacement_func in patterns:
            normalized_input = re.sub(pattern, lambda m: f"on {replacement_func(m)}", normalized_input, flags=re.IGNORECASE)
        
        # Log if changes were made
        if normalized_input != user_input:
            logger.info(f"Normalized date expressions: '{user_input}' -> '{normalized_input}'")
            
        return normalized_input
    
    def process_natural_language(self, user_input):
        """Process natural language input to extract calendar event or todo information."""
        # Normalize relative date expressions
        normalized_input = self.normalize_relative_dates(user_input)
        
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        next_month = today + timedelta(days=30)
        
        # Get relevant memories if memory manager is available
        memory_context = ""
        if self.memory_manager:
            relevant_memories = self.memory_manager.get_relevant_memories(normalized_input, limit=3)
            if relevant_memories:
                memory_context = "\n\nRelevant past interactions:\n"
                for memory in relevant_memories:
                    memory_context += f"- User asked: '{memory['user_input']}'\n"
        
        prompt = f"""
        Extract information from the following text. 
        Return a JSON object with the following fields if present in the text:
        
        For calendar events:
        - event_name: The name or title of the event
        - start_date: The start date and time of the event
        - end_date: The end date and time of the event
        - description: A description of the event
        - location: The location of the event
        - participants: A list of participants or a string with participant names
        
        For todo items:
        - task_name: The name of the task
        - due_date: The due date for the task
        - priority: The priority level (high, medium, low)
        - status: The status of the task (not started, in progress, completed)
        - notes: Any additional notes about the task
        
        For date references, understand relative terms like:
        - "today" = {today.strftime('%Y-%m-%d')}
        - "tomorrow" = {tomorrow.strftime('%Y-%m-%d')}
        - "next week" = starting {next_week.strftime('%Y-%m-%d')}
        - "next month" = starting {next_month.strftime('%Y-%m-%d')}
        - "in 2 days" or "after 2 days" = {(today + timedelta(days=2)).strftime('%Y-%m-%d')}
        - "in 3 days" or "after 3 days" = {(today + timedelta(days=3)).strftime('%Y-%m-%d')}
        - "a couple of days from now" = {(today + timedelta(days=2)).strftime('%Y-%m-%d')}
        - "in a week" or "after a week" = {(today + timedelta(days=7)).strftime('%Y-%m-%d')}
        
        Handle phrases like "after a few days", "in several days", or "within X days" appropriately.
        
        Only include fields that are explicitly mentioned in the text.
        {memory_context}
        
        Text: {normalized_input}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            
            # Store this interaction if memory manager is available
            if self.memory_manager:
                self.memory_manager.add_interaction(
                    user_input=user_input,
                    agent_response={"type": "process_natural_language", "result": result}
                )
                
            return result
        except Exception as e:
            logger.error(f"Error processing natural language with Gemini API: {str(e)}")
            return {}
    
    def suggest_calendar_actions(self, user_input, current_events=None):
        """Suggest actions to take based on user input and current calendar events."""
        events_context = ""
        if current_events:
            events_str = "\n".join([f"- {e.get('event_name', 'Untitled')}: {e.get('start_date', 'No date')}" 
                                for e in current_events[:5]])
            events_context = f"\n\nCurrent calendar events:\n{events_str}"
        
        # Get relevant memories if memory manager is available
        memory_context = ""
        if self.memory_manager:
            relevant_memories = self.memory_manager.get_relevant_memories(user_input, limit=2)
            if relevant_memories:
                memory_context = "\n\nRelevant past interactions:\n"
                for memory in relevant_memories:
                    memory_context += f"- User asked: '{memory['user_input']}'\n"
                    if "agent_response" in memory and "action" in memory["agent_response"]:
                        memory_context += f"  Action taken: {memory['agent_response']['action']}\n"
        
        prompt = f"""
        Based on the user's request and their current calendar events, determine the most appropriate action to take.
        Return a JSON object with the following fields:
        - action: One of ["create", "read", "update", "delete", "unknown"]
        - event_id: If the action is update or delete, the ID of the event to modify (if mentioned or can be inferred)
        - reason: A brief explanation of why this action was chosen
        
        User request: {user_input}{events_context}{memory_context}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            
            # Ensure we return a dictionary
            if not isinstance(result, dict):
                print(f"Warning: Parsed response is not a dictionary: {result}")
                return {"action": "unknown", "reason": "Failed to parse response correctly"}
            
            # Store this interaction if memory manager is available
            if self.memory_manager:
                self.memory_manager.add_interaction(
                    user_input=user_input,
                    agent_response={"type": "suggest_calendar_actions", "action": result.get("action", "unknown")}
                )
            
            return result
        except Exception as e:
            print(f"Error suggesting calendar actions with Gemini API: {str(e)}")
            return {"action": "unknown", "reason": "Failed to process request"}
    
    def generate_event_summary(self, events):
        """Generate a natural language summary of calendar events."""
        if not events:
            return "You don't have any events scheduled."
        
        events_str = "\n".join([f"- {e.get('event_name', 'Untitled')}: {e.get('start_date', 'No date')}" 
                            for e in events])
        
        # Get user preferences if memory manager is available
        style_preference = ""
        if self.memory_manager:
            summary_style = self.memory_manager.get_preference("summary_style", "informative")
            if summary_style == "brief":
                style_preference = "Keep the summary very brief and to the point."
            elif summary_style == "detailed":
                style_preference = "Provide a detailed summary with all available information."
            else:  # informative
                style_preference = "The summary should be informative and conversational."
        
        prompt = f"""
        Generate a concise, natural-sounding summary of the following calendar events:
        
        {events_str}
        
        {style_preference} Mention key events and their timing.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating event summary with Gemini API: {str(e)}")
            return "I found some events in your calendar, but couldn't generate a summary."
    
    def _parse_response(self, response_text):
        """Parse the response text to extract JSON data."""
        import json
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'```json\n(.+?)\n```', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # If no JSON code block, try to find anything that looks like JSON
            json_match = re.search(r'\{.+\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                return {}
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON from response: {response_text}")
            return {}
    
    def process_natural_language(self, text):
        """Process natural language text to extract structured information."""
        # Get relevant memories if memory manager is available
        memory_context = ""
        if self.memory_manager:
            relevant_memories = self.memory_manager.get_relevant_memories(text, limit=3)
            if relevant_memories:
                memory_context = "\n\nRelevant past interactions:\n"
                for memory in relevant_memories:
                    memory_context += f"- User asked: '{memory['user_input']}'\n"
        
        prompt = f"""
        Extract structured information from the following text for a todo item or calendar event.
        For todo items, extract:
        - task_name: A concise, clear name for the task (don't include the entire input as the task name)
        - due_date: When the task is due (if mentioned)
        - status: The status of the task (e.g., "Not Started", "In Progress", "Completed")
        - priority: The priority of the task (e.g., "Low", "Medium", "High")
        - notes: Any additional notes about the task
        
        For calendar events, extract:
        - event_name: A concise name for the event
        - start_date: When the event starts
        - end_date: When the event ends (if mentioned)
        - description: Description of the event
        - location: Where the event takes place (if mentioned)
        - participants: Who is participating (if mentioned)
        
        Return the information as a JSON object with only the fields that are present in the text.
        {memory_context}
        
        Text: {text}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            
            # Store this interaction if memory manager is available
            if self.memory_manager and result:
                self.memory_manager.add_interaction(
                    user_input=text,
                    agent_response={"type": "process_natural_language", "result": result}
                )
                
            return result
        except Exception as e:
            print(f"Error processing natural language with Gemini API: {str(e)}")
            return None
    
    def suggest_todo_actions(self, user_input, current_todos=None):
        """Suggest actions to take based on user input and current todo items."""
        todos_context = ""
        if current_todos:
            todos_str = "\n".join([f"- {t.get('task_name', 'Untitled')}: due {t.get('due_date', 'No date')}" 
                                for t in current_todos[:5]])
            todos_context = f"\n\nCurrent todo items:\n{todos_str}"
        
        # Get relevant memories if memory manager is available
        memory_context = ""
        if self.memory_manager:
            relevant_memories = self.memory_manager.get_relevant_memories(user_input, limit=2)
            if relevant_memories:
                memory_context = "\n\nRelevant past interactions:\n"
                for memory in relevant_memories:
                    memory_context += f"- User asked: '{memory['user_input']}'\n"
                    if "agent_response" in memory and "action" in memory["agent_response"]:
                        memory_context += f"  Action taken: {memory['agent_response']['action']}\n"
        
        prompt = f"""
        Based on the user's request and their current todo items, determine the most appropriate action to take.
        Return a JSON object with the following fields:
        - action: One of ["create", "read", "update", "delete", "unknown"]
        - todo_id: If the action is update or delete, the ID of the todo to modify (if mentioned or can be inferred)
        - reason: A brief explanation of why this action was chosen
    
        User request: {user_input}{todos_context}{memory_context}
        """
        
        try:
            response = self.model.generate_content(prompt)
            result = self._parse_response(response.text)
            
            # Ensure we return a dictionary
            if not isinstance(result, dict):
                print(f"Warning: Parsed response is not a dictionary: {result}")
                return {"action": "unknown", "reason": "Failed to parse response correctly"}
            
            # Store this interaction if memory manager is available
            if self.memory_manager:
                self.memory_manager.add_interaction(
                    user_input=user_input,
                    agent_response={"type": "suggest_todo_actions", "action": result.get("action", "unknown")}
                )
            
            return result
        except Exception as e:
            print(f"Error suggesting todo actions with Gemini API: {str(e)}")
            return {"action": "unknown", "reason": "Failed to process request"}
    
    def generate_todo_summary(self, todos):
        """Generate a natural language summary of todo items."""
        if not todos:
            return "You don't have any todo items."
        
        todos_str = "\n".join([f"- {t.get('task_name', 'Untitled')}: due {t.get('due_date', 'No date')}, " +
                              f"status: {t.get('status', 'Not specified')}" for t in todos])
        
        # Get user preferences if memory manager is available
        style_preference = ""
        if self.memory_manager:
            summary_style = self.memory_manager.get_preference("summary_style", "informative")
            if summary_style == "brief":
                style_preference = "Keep the summary very brief and to the point."
            elif summary_style == "detailed":
                style_preference = "Provide a detailed summary with all available information."
            else:  # informative
                style_preference = "The summary should be informative and helpful."
        
        prompt = f"""
        Generate a brief, helpful summary of these todo items:
        
        {todos_str}
        
        {style_preference} Include information about priorities, upcoming deadlines, and overall status.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error generating todo summary with Gemini API: {str(e)}")
            return "Here are your todo items."

    