from core.orchestrator import Orchestrator
from dotenv import load_dotenv
import os
import json

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Initialize the agent selector
    orchestrator = Orchestrator()
    
    print("Welcome to Notion Agent!")
    print("You can manage your calendar events or todo items using natural language.")
    print("Type 'exit' to quit, 'help' for commands, or 'insights' to see usage patterns.")
    
    while True:
        # Get user input
        user_input = input("\nWhat would you like to do with Notion? ")
        
        # Check if user wants to exit
        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("Goodbye!")
            break
        
        # Check for special commands
        if user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit/quit/bye: Exit the application")
            print("- insights: Show insights about your usage patterns")
            print("- preference [key] [value]: Set a preference (e.g., 'preference summary_style brief')")
            print("- Any natural language request for calendar or todo management")
            continue
            
        elif user_input.lower() == 'insights':
            insights = orchestrator.get_insights()
            print("\n=== Usage Insights ===")
            print(f"Total interactions: {insights['system']['total_interactions']}")
            
            print("\nCommon patterns:")
            for pattern, freq in insights['system']['common_patterns']:
                print(f"- '{pattern}': used {freq} times")
            
            print("\nPreferences:")
            for key, value in insights['system']['preferences'].items():
                print(f"- {key}: {value['value']}")
            continue
            
        elif user_input.lower().startswith('preference '):
            # Parse preference command: preference [key] [value]
            parts = user_input.split(' ', 2)
            if len(parts) >= 3:
                key = parts[1]
                value = parts[2]
                orchestrator.update_preference(key, value)
                print(f"✅ Preference '{key}' set to '{value}'")
            else:
                print("❌ Invalid preference format. Use: preference [key] [value]")
            continue
        
        # Process the request with the appropriate agent
        result = orchestrator.process_request(user_input)
        
        # Display the result
        if result.get("status") == "success":
            print(f"\n✅ {result.get('message')}")
            
            # If there are events in the result, display them
            if "events" in result and result["events"] and result["status"] == "success":
                print("\nEvents:")
                for event in result["events"]:
                    print(f"- {event.get('event_name', 'Untitled')}: {event.get('start_date', 'No date')}")
            
            # If there are todos in the result, display them
            if "todos" in result and result["todos"] and result["status"] == "success":
                print("\nTodo Items:")
                for todo in result["todos"]:
                    print(f"- {todo.get('task_name', 'Untitled')}: due {todo.get('due_date', 'No date')}, " +
                          f"status: {todo.get('status', 'Not specified')}")
        else:
            print(f"\n❌ {result.get('message', 'An error occurred.')}")

if __name__ == "__main__":
    main()