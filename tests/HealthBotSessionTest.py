from langgraph.graph import END

from health_chatbot.health_bot import create_health_bot_graph, draw_workflow_diagram
from health_chatbot.health_bot_session import HealthBotSession


def main():
    """Simple script to test the refactored HealthBotSession"""

    # Build the graph first
    graph = create_health_bot_graph()
    draw_workflow_diagram(graph)

    # Create a session with an initial question and the graph
    session = HealthBotSession("What are tension headache "
                               "symptoms?", graph, END)

    # Get the generator
    conversation = session.run_conversation()

    # Test the conversation flow
    try:
        step = 1
        while True:
            print(f"=== STEP {step} ===")
            try:
                response = next(conversation)
            except StopIteration:
                print("Generator ended - no more responses")
                break
            
            if response.message:
                # Bot sent a message
                print("=== AGENT MESSAGE ===")
                print(f"Message: {response.message}")
                if response.information_source:
                    print(f"Source: {response.information_source}")
                print("=" * 50)
                
            elif response.user_input_request:
                # Bot is asking for user input
                request = response.user_input_request
                print("=== INPUT REQUEST ===")
                print(f"Prompt: {request.prompt}")
                print(f"Type: {request.input_type}")
                if request.options:
                    print(f"Options: {request.options}")
                print("=" * 30)
                
                # Simulate user response based on input type
                if request.input_type == "quiz_choice":
                    user_input = "yes"
                elif request.input_type == "quiz_answer":
                    user_input = "headache, sensitivity to light"
                elif request.input_type == "new_topic_choice":
                    user_input = "no"  # End conversation
                elif request.input_type == "new_question":
                    user_input = "What causes migraines?"
                else:
                    user_input = "yes"  # Default
                    
                print(f"User response: {user_input}")
                print("=" * 50)
                
                # Send the response back to the generator
                conversation.send(user_input)
                
            step += 1
                
    except StopIteration:
        print("=== CONVERSATION ENDED ===")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
