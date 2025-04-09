import os
import json
from datetime import datetime
import hashlib

class MemoryManager:
    """Manages memory for agents, storing interactions and patterns."""
    
    def __init__(self, memory_type="system"):
        """Initialize the memory manager.
        
        Args:
            memory_type (str): Type of memory to manage (system, calendar, todo)
        """
        # Ensure memory files are stored in the memory directory
        memory_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory")
        
        # Create memory directory if it doesn't exist
        os.makedirs(memory_dir, exist_ok=True)
        
        self.memory_file = os.path.join(memory_dir, f"memory_{memory_type}.json")
        self.memories = self._load_memories()
    
    def _load_memories(self):
        """Load memories from the memory file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"Error loading memory file. Creating new memory.")
                return {"interactions": [], "patterns": {}, "preferences": {}}
        else:
            return {"interactions": [], "patterns": {}, "preferences": {}}
    
    def _save_memories(self):
        """Save memories to the memory file."""
        with open(self.memory_file, 'w') as f:
            json.dump(self.memories, f, indent=2)
    
    def add_interaction(self, user_input, agent_response, metadata=None):
        """Add a new interaction to memory.
        
        Args:
            user_input (str): The user's input
            agent_response (dict): The agent's response
            metadata (dict, optional): Additional metadata about the interaction
        """
        # Generate a unique ID for this interaction
        interaction_id = hashlib.md5(f"{user_input}_{datetime.now().isoformat()}".encode()).hexdigest()
        
        # Create the interaction record
        interaction = {
            "id": interaction_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "agent_response": agent_response,
            "metadata": metadata or {}
        }
        
        # Add to interactions list
        self.memories["interactions"].append(interaction)
        
        # Update patterns based on this interaction
        self._update_patterns(user_input, agent_response)
        
        # Save the updated memories
        self._save_memories()
    
    def _update_patterns(self, user_input, agent_response):
        """Update recognized patterns based on user interactions.
        
        Args:
            user_input (str): The user's input
            agent_response (dict): The agent's response
        """
        # Extract keywords from user input
        keywords = self._extract_keywords(user_input)
        
        # Update frequency of patterns
        for keyword in keywords:
            if keyword in self.memories["patterns"]:
                self.memories["patterns"][keyword]["frequency"] += 1
            else:
                self.memories["patterns"][keyword] = {
                    "frequency": 1,
                    "last_seen": datetime.now().isoformat(),
                    "examples": []
                }
            
            # Add this as an example if we don't have too many
            if len(self.memories["patterns"][keyword]["examples"]) < 5:
                example = {
                    "input": user_input,
                    "response_status": agent_response.get("status", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
                self.memories["patterns"][keyword]["examples"].append(example)
    
    def _extract_keywords(self, text):
        """Extract important keywords from text.
        
        Args:
            text (str): The text to extract keywords from
            
        Returns:
            list: List of extracted keywords
        """
        # Simple keyword extraction - split by spaces and filter out common words
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with", "by", "about", "like"}
        words = text.lower().split()
        keywords = [word for word in words if word not in common_words and len(word) > 3]
        return keywords
    
    def get_relevant_memories(self, user_input, limit=5):
        """Get memories relevant to the current user input.
        
        Args:
            user_input (str): The user's current input
            limit (int): Maximum number of memories to return
            
        Returns:
            list: List of relevant past interactions
        """
        keywords = self._extract_keywords(user_input)
        
        # Score each past interaction based on keyword overlap
        scored_interactions = []
        for interaction in self.memories["interactions"]:
            past_input = interaction["user_input"]
            past_keywords = self._extract_keywords(past_input)
            
            # Calculate overlap score
            overlap = len(set(keywords).intersection(set(past_keywords)))
            if overlap > 0:
                scored_interactions.append((overlap, interaction))
        
        # Sort by score (highest first) and return top matches
        scored_interactions.sort(key=lambda x: x[0], reverse=True)
        return [interaction for _, interaction in scored_interactions[:limit]]
    
    def update_preference(self, preference_key, preference_value):
        """Update a user preference.
        
        Args:
            preference_key (str): The preference identifier
            preference_value: The preference value
        """
        self.memories["preferences"][preference_key] = {
            "value": preference_value,
            "updated_at": datetime.now().isoformat()
        }
        self._save_memories()
    
    def get_preference(self, preference_key, default=None):
        """Get a user preference.
        
        Args:
            preference_key (str): The preference identifier
            default: Default value if preference doesn't exist
            
        Returns:
            The preference value or default
        """
        if preference_key in self.memories["preferences"]:
            return self.memories["preferences"][preference_key]["value"]
        return default
     
    def get_common_patterns(self, limit=10):
        """Get the most common usage patterns.
        
        Args:
            limit (int): Maximum number of patterns to return
            
        Returns:
            list: List of (pattern, frequency) tuples
        """
        patterns = [(k, v["frequency"]) for k, v in self.memories["patterns"].items()]
        patterns.sort(key=lambda x: x[1], reverse=True)
        return patterns[:limit]
    
    def generate_insights(self):
        """Generate insights about user behavior based on stored memories.
        
        Returns:
            dict: Dictionary of insights
        """
        # Get common patterns
        common_patterns = self.get_common_patterns(5)
        
        # Count total interactions
        total_interactions = len(self.memories["interactions"])
        
        # Get preferences
        preferences = self.memories["preferences"]
        
        insights = {
            "total_interactions": total_interactions,
            "common_patterns": common_patterns,
            "preferences": preferences,
        }
        
        return insights