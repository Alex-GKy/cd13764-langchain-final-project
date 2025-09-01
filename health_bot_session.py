import uuid
from dataclasses import dataclass
from typing import Optional, Generator

from langchain_core.runnables import RunnableConfig


def normalize_information_source(information_source: str) -> str:
    """Normalize internal agent source names to unified identifiers"""
    source_mapping = {
        "rag": "rag",
        "agent_knowledge": "knowledge",
        "web_search": "web"
    }
    return source_mapping.get(information_source, "unknown")


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
    information_source: Optional[str] = None

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

        first_iteration = True

        while True:
            # Stream with input only on first iteration
            stream_input = {
                "user_question": self.initial_question} \
                    if first_iteration else None

            first_iteration = False

            # Stream the graph until it stops (interrupt or end)
            for event in self.graph.stream(input=stream_input,
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

                        # get the message and source type
                        content = message.content
                        raw_source = event.get("information_source")
                        normalized_source = normalize_information_source(
                            raw_source) if raw_source else None

                        yield BotResponse(message=content,
                                          information_source=normalized_source)

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

            elif next_node == "grade_quiz":
                input_request = UserInputRequest(
                    prompt="Please state your answer:",
                    input_type="quiz_answer")
                user_response = yield BotResponse(
                    user_input_request=input_request)
                self.graph.update_state(self.config,
                                        {"quiz_answer": user_response})

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
                first_iteration = True  # Reset flag for new conversation
