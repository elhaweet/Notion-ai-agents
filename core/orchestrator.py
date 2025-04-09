from agents.calendar_agent import CalendarAgent
from agents.todo_agent import TodoAgent
from clients.gemini_client import GeminiClient
from memory.memory_manager import MemoryManager
import logging


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Orchestrator:
    """Selects the appropriate agent based on user input."""
    
    def __init__(self):
        """Initialize the agent selector."""
        # Initialize memory managers
        self.system_memory = MemoryManager("system")
        self.calendar_memory = MemoryManager("calendar")
        self.todo_memory = MemoryManager("todo")
        
        # Initialize Gemini client with system memory
        self.gemini_client = GeminiClient(memory_manager=self.system_memory)
        
        # Initialize agents with their respective memory managers
        self.calendar_agent = CalendarAgent(memory_manager=self.calendar_memory)
        self.todo_agent = TodoAgent(memory_manager=self.todo_memory)
        
        self.current_agent = None
    
    def determine_agent_type(self, user_input):
        """Determine whether the user input is related to calendar or todo functionality.
        
        Args:
            user_input (str): The user's natural language input
            
        Returns:
            str: Either "calendar", "todo", or "unknown"  (the agents that we have)
        """
        # Calendar-related keywords
        calendar_keywords = [
            "calendar", "event", "meeting", "appointment", "schedule", 
            "remind me about", "when is", "reschedule", "cancel meeting",
            "book", "reservation", "conference", "seminar", "workshop",
            "class", "lecture", "presentation", "interview"
        ]
        
        # Todo-related keywords
        todo_keywords = [
            "todo", "task", "reminder", "checklist", "to-do", "to do",
            "complete", "finish", "done", "mark", "check off", "add task",
            "add item", "shopping list", "grocery", "buy", "purchase",
            "assignment", "homework", "project", "deadline"
        ]
        
        # Convert input to lowercase for case-insensitive matching
        input_lower = user_input.lower()
        
        # Optimized keyword matching using any() and generator expressions
        if any(keyword in input_lower for keyword in calendar_keywords):
            return "calendar"
        
        if any(keyword in input_lower for keyword in todo_keywords):
            return "todo"
        
        # If no clear match, use Gemini for more sophisticated analysis
        try:
            # Check if we have a memory of similar requests with high similarity
            relevant_memories = self.system_memory.get_relevant_memories(user_input, limit=3)
            
            # Only use memory if it's recent or highly relevant
            for memory in relevant_memories:
                if "agent_type" in memory.get("metadata", {}) and memory.get("similarity_score", 0) > 0.8:
                    return memory["metadata"]["agent_type"]
            
            prompt = f"""
            Analyze the following user input and determine if it's related to:
            1. Calendar events/scheduling (return "calendar")
            2. Todo items/tasks (return "todo")
            3. Neither (return "unknown")
            
            Only respond with one of these three words: "calendar", "todo", or "unknown".
            
            User input: {user_input}
            """
            
            response = self.gemini_client.model.generate_content(prompt)
            result = response.text.strip().lower()
            
            if result in ["calendar", "todo"]:
                return result
            else:
                return "unknown"
            
        except Exception as e:
            logger.error(f"Error using Gemini for agent type determination: {str(e)}")
            # Default to unknown if there's an error
            return "unknown"
    
    def process_request(self, user_input):
        """Process a user request and route it to the appropriate agent."""
        # Use the local method to determine if this is a calendar or todo request
        agent_type = self.determine_agent_type(user_input)
        
        # Store this determination in memory
        self.system_memory.add_interaction(
            user_input=user_input,
            agent_response={"status": "processing", "agent_type": agent_type},
            metadata={"agent_type": agent_type}
        )
        
        result = None
        if agent_type == "calendar":
            result = self.calendar_agent.process_request(user_input)
        elif agent_type == "todo":
            # Use a helper method to check if this is a "mark as done" request
            if self._is_mark_done_request(user_input):
                result = self.todo_agent.mark_todo_as_done(user_input)
            else:
                result = self.todo_agent.process_request(user_input)
        else:
            result = {
                "status": "error",
                "message": "I'm not sure if you want to manage calendar events or todo items. Please be more specific."
            }
        
        # Store the result in memory
        self.system_memory.add_interaction(
            user_input=user_input,
            agent_response=result,
            metadata={"agent_type": agent_type, "result_status": result.get("status", "unknown")}
        )
        
        return result
    
    def _is_mark_done_request(self, user_input):
        """Helper method to determine if a request is about marking a todo as done.
        
        Args:
            user_input (str): The user's natural language input
            
        Returns:
            bool: True if this appears to be a mark-as-done request
        """
        mark_done_keywords = ["done", "complete", "finished", "completed", "mark", "check off"]
        input_lower = user_input.lower()
        
        return any(keyword in input_lower for keyword in mark_done_keywords)
    
    def get_insights(self):
        """Get insights about user behavior from memory.
        
        Returns:
            dict: Dictionary of insights
        """
        try:
            system_insights = self.system_memory.generate_insights()
        except Exception as e:
            logger.error(f"Error generating system insights: {str(e)}")
            system_insights = {"total_interactions": 0, "common_patterns": [], "preferences": {}}
        
        try:
            calendar_insights = self.calendar_memory.generate_insights()
        except Exception as e:
            logger.error(f"Error generating calendar insights: {str(e)}")
            calendar_insights = {"total_interactions": 0, "common_patterns": [], "preferences": {}}
        
        try:
            todo_insights = self.todo_memory.generate_insights()
        except Exception as e:
            logger.error(f"Error generating todo insights: {str(e)}")
            todo_insights = {"total_interactions": 0, "common_patterns": [], "preferences": {}}
        
        return {
            "system": system_insights,
            "calendar": calendar_insights,
            "todo": todo_insights
        }
    
    def update_preference(self, preference_key, preference_value):
        """Update a user preference across all memory managers.
        
        Args:
            preference_key (str): The preference identifier
            preference_value: The preference value
        """
        self.system_memory.update_preference(preference_key, preference_value)
        self.calendar_memory.update_preference(preference_key, preference_value)
        self.todo_memory.update_preference(preference_key, preference_value)