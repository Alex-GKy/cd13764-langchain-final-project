from langchain_core.runnables import RunnableConfig
from dataclasses import dataclass
import uuid
from typing import Optional


@dataclass
class UserInputRequest:
    """Represents a request for user input that the UI should handle"""
    prompt: str
    input_type: str  # "quiz_choice", "quiz_answer", "new_topic_choice", "new_question"
    options: list = None  # For multiple choice questions


class HealthBotSession:
    """
    Session-based health bot that processes one step at a time.
    The graph manages the flow, we just translate states to UI actions.
    """

    def __init__(self, initial_question: str, graph, END):
        self.thread_id = str(uuid.uuid4())
        self.config = RunnableConfig()
        self.config["configurable"] = {"thread_id": self.thread_id}
        self.last_printed_message_id = None
        self.initial_question = initial_question
        self.graph = graph
        self.END = END

    def _get_source_prefix(self, information_source: str) -> str:
        """Get the source prefix based on the information source"""

        source_prefixes = {
            "rag": "📚 Based on our curated health documents:\n\n",
            "agent_knowledge": "🧠 Based on my general medical knowledge:\n\n",
            "web_search": "🔍 Based on recent web search results:\n\n"
        }
        return source_prefixes.get(information_source, "")

    def run_conversation(self):
        """Generator that yields AI messages and UserInputRequests, expects
        user responses via send()"""

        input_data = {"user_question": self.initial_question}

        while True:
            # Stream the graph until it stops (interrupt or end)
            for event in self.graph.stream(input=input_data, config=self.config,
                                  stream_mode="values"):
                if messages := event.get("messages", []):
                    message = messages[-1]
                    if (
                            message.id != self.last_printed_message_id and
                            message.type == "ai" and message.content):
                        self.last_printed_message_id = message.id
                        
                        # Check if we have source information and prepend it
                        content = message.content
                        if information_source := event.get("information_source"):
                            source_prefix = self._get_source_prefix(information_source)
                            content = source_prefix + content
                        
                        yield content  # Yield AI message with source prefix

            # Check what's next after streaming stops
            state = self.graph.get_state(self.config)
            next_node = state.next[0] if state.next else None

            if not next_node or next_node == self.END:
                return  # Conversation done

            # Yield appropriate input request and wait for user response
            if next_node == "ask_for_quiz":
                user_response = yield UserInputRequest(
                    prompt="Would you like to do a quiz about this topic?",
                    input_type="quiz_choice", options=["Yes", "No"])
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                self.graph.update_state(self.config, {"quiz_choice": choice})
                input_data = None  # No new input data needed, just continue

            elif next_node == "grade_quiz":
                user_response = yield UserInputRequest(
                    prompt="Please state your answer:",
                    input_type="quiz_answer")
                self.graph.update_state(self.config, {"quiz_answer": user_response})
                input_data = None

            elif next_node == "ask_for_new_topic":
                user_response = yield UserInputRequest(
                    prompt="Would you like to discuss another topic?",
                    input_type="new_topic_choice", options=["Yes", "No"])
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                self.graph.update_state(self.config, {"new_topic_choice": choice})
                input_data = None

            elif next_node == "ask_topic_question":
                user_response = yield UserInputRequest(
                    prompt="What health topic would you like me to research?",
                    input_type="new_question")
                # For new questions, we reset and restart with new input
                self.initial_question = user_response
                self.last_printed_message_id = None
                # Clear the thread to start fresh
                self.thread_id = str(uuid.uuid4())
                self.config["configurable"]["thread_id"] = self.thread_id
                input_data = {"user_question": user_response}