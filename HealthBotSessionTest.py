from langgraph.graph import END

from health_bot import create_health_bot_graph
from health_bot_session import HealthBotSession


def main():
    """Simple script to test the refactored HealthBotSession"""

    # Build the graph first
    graph = create_health_bot_graph()

    # Create a session with an initial question and the graph
    session = HealthBotSession("What are tension headache symptoms?", graph,
                               END)

    # Get the generator
    conversation = session.run_conversation()

    # Get the first response
    try:
        response = next(conversation)
        print("=== AGENT RESPONSE ===")
        print(f"Response: {response}")
        print("=" * 50)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
