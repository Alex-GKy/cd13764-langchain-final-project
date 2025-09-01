import uuid
from dataclasses import dataclass
from typing import Optional, Generator

from langchain_core.runnables import RunnableConfig


def get_source_prefix(information_source: str) -> str:
    """Get the source prefix based on the information source"""
    source_prefixes = {
        "rag": "📚 Based on our curated health documents:\n\n",
        "agent_knowledge": "🧠 Based on my general medical knowledge:\n\n",
        "web_search": "🔍 Based on recent web search results:\n\n"
    }
    return source_prefixes.get(information_source, "")


@dataclass
class UserInputRequest:
    """Represents a request for user input that the UI should handle"""
    prompt: str
    input_type: str  # "quiz_choice", "quiz_answer", "new_topic_choice", 
    # "new_question"
    options: list = None  # For multiple choice questions


@dataclass
class BotResponse:
    """Unified response from the HealthBot - either a message or input
    request"""
    message: Optional[str] = None
    user_input_request: Optional[UserInputRequest] = None

    def __post_init__(self):
        # Ensure exactly one of message or user_input_request is provided
        if (self.message is None) == (self.user_input_request is None):
            raise ValueError(
                "Exactly one of 'message' or 'user_input_request' must be "
                "provided")


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

    def run_conversation(self) -> Generator[BotResponse, str, None]:

        """Generator that yields AI messages and UserInputRequests, expects
        user responses via send()"""

        input_data = {"user_question": self.initial_question}

        while True:
            # Stream the graph until it stops (interrupt or end)
            for event in self.graph.stream(input=input_data,
                                           config=self.config,
                                           stream_mode="values"):

                # if the current event has a message from the agent
                if messages := event.get("messages", []):
                    message = messages[-1]

                    # check if it' an ai message and we've not printed it yet
                    if (
                            message.id != self.last_printed_message_id and
                            message.type == "ai" and message.content):

                        self.last_printed_message_id = message.id
                        content = message.content

                        # Check if we have source information and prepend it
                        if information_source := event.get(
                                "information_source"):
                            source_prefix = get_source_prefix(
                                information_source)
                            content = source_prefix + content

                        yield BotResponse(message=content)

            # Check what's next after streaming stops
            state = self.graph.get_state(self.config)
            next_node = state.next[0] if state.next else None

            if not next_node or next_node == self.END:
                return  # Conversation done

            # Yield appropriate input request and wait for user response
            if next_node == "ask_for_quiz":
                input_request = UserInputRequest(
                    prompt="Would you like to do a quiz about this topic?",
                    input_type="quiz_choice", options=["Yes", "No"])
                user_response = yield BotResponse(
                    user_input_request=input_request)
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                self.graph.update_state(self.config, {"quiz_choice": choice})
                input_data = None  # No new input data needed, just continue

            elif next_node == "grade_quiz":
                input_request = UserInputRequest(
                    prompt="Please state your answer:",
                    input_type="quiz_answer")
                user_response = yield BotResponse(
                    user_input_request=input_request)
                self.graph.update_state(self.config,
                                        {"quiz_answer": user_response})
                input_data = None

            elif next_node == "ask_for_new_topic":
                input_request = UserInputRequest(
                    prompt="Would you like to discuss another topic?",
                    input_type="new_topic_choice", options=["Yes", "No"])
                user_response = yield BotResponse(
                    user_input_request=input_request)
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                self.graph.update_state(self.config,
                                        {"new_topic_choice": choice})
                input_data = None

            elif next_node == "ask_topic_question":
                input_request = UserInputRequest(
                    prompt="What health topic would you like me to research?",
                    input_type="new_question")
                user_response = yield BotResponse(
                    user_input_request=input_request)
                # For new questions, we reset and restart with new input
                self.initial_question = user_response
                self.last_printed_message_id = None
                # Clear the thread to start fresh
                self.thread_id = str(uuid.uuid4())
                self.config["configurable"]["thread_id"] = self.thread_id
                input_data = {"user_question": user_response}
