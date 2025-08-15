from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END, add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage
from tavily import TavilyClient
from typing import Dict, Union, Optional
from dataclasses import dataclass
import os
import mlflow
import uuid
from langchain_core.tools import tool
from health_rag_service import health_rag
from prompt_library import get_system_prompt

# MLFlow setup
try:
    mlflow.set_tracking_uri(
        os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
    mlflow.set_experiment("health_bot")
    mlflow.langchain.autolog()
except:
    print("MLflow server not running. Proceeding without MLflow.")

# base_url = "https://openai.vocareum.com/v1"
base_url = "https://api.openai.com/v1"
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, base_url=base_url)


@dataclass
class UserInputRequest:
    """Represents a request for user input that the UI should handle"""
    prompt: str
    input_type: str  # "quiz_choice", "quiz_answer", "new_topic_choice",
    # "new_question"
    options: list = None  # For multiple choice questions


class State(MessagesState):
    user_question: str
    summary: str
    comprehension_question: str
    quiz_answer: str
    quiz_choice: str
    new_topic_choice: str
    information_source: Optional[str]


def entry_point(state: State):
    # Starting node
    system_message = get_system_prompt("rag_with_fallback")

    human_message = HumanMessage(state["user_question"])
    messages = add_messages(system_message, human_message)

    return {"messages": messages}


def agent(state: State):
    # Research agent
    ai_message = llm.invoke(state["messages"])
    return {"messages": [ai_message]}


def route_to_tool(state: State):
    # Routes to web search tool
    last_message = state["messages"][-1]

    # TODO need to decide which tool use here
    if last_message.tool_calls:
        return "search_health_documents"
    else:
        return END


def route_after_rag(state: State):
    """Route after RAG search - check if we need to use agent's own
    knowledge"""

    last_message = state["messages"][-1]

    # Check if the RAG search didn't find relevant documents
    if (hasattr(last_message,
                'content') and last_message.content ==
            "NO_RELEVANT_DOCUMENTS_FOUND"):
        return "agent_knowledge"

    elif (hasattr(last_message,
                  'content') and last_message.content ==
          "RAG_SERVICE_UNAVAILABLE"):
        return "agent_knowledge"

    else:
        return "summarize"


def agent_knowledge(state: State):
    """Use agent's own knowledge when RAG doesn't find relevant documents"""

    # Create a separate LLM instance without tools for agent knowledge fallback
    # Otherwise it will try to use a tool call
    llm_no_tools = ChatOpenAI(model="gpt-4o-mini",
                              temperature=0.2,
                              base_url=base_url)

    # Get the original user question from the state
    user_question = state.get("user_question", "")

    print(f"🧠 Using agent knowledge to answer: {user_question}")

    # Create a system message for using agent's own knowledge
    system_message = SystemMessage(
        "The health document search didn't find relevant documents for this "
        "question. "
        "Use your own knowledge to provide a helpful, accurate response "
        "about this health topic. "
        "Provide comprehensive information including:\n"
        "- Overview of the condition/topic\n"
        "- Common symptoms if applicable\n"
        "- Potential causes if relevant\n"
        "- General management or treatment approaches\n"
        "- When to seek medical help\n\n"
        "Be informative but also mention that the user should consult with "
        "healthcare "
        "professionals for personalized medical advice. "
        "Structure your response clearly with helpful sections."
        "Limit your response to 2-3 paragraphs max")

    # Create a new human message with just the user's question
    human_message = HumanMessage(user_question)

    # Use the LLM WITHOUT tools to get response using agent's knowledge
    ai_message = llm_no_tools.invoke([system_message, human_message])

    # Store this as the summary for later use in quiz generation
    return {
        "messages": [ai_message],
        "summary": ai_message.content,
        "information_source": "agent_knowledge"  # Add this line
    }


@tool
def search_health_documents(query: str) -> str:
    """
    Search through health documents for relevant information.

    Use this tool when users ask questions about:
    - Headaches, migraines, tension headaches
    - Back pain, neck pain
    - Stress management for pain relief
    - Symptoms, causes, treatments, prevention

    Args:
        query: The health question or topic to search for

    Returns:
        Relevant health information or a message if no relevant content found
    """

    # Initialize RAG service if not already done
    if not health_rag.is_initialized:

        print("Initializing Health RAG Service...")

        if not health_rag.initialize():
            return "RAG_SERVICE_UNAVAILABLE"

        health_rag.set_relevance_threshold(
            0.8)  # Use higher threshold for better precision

    # Get context for the query
    context = health_rag.get_context_for_query(query)

    if context:
        return (f"Here's relevant information from our health documents:\n\n"
                f"{context}")
    else:
        return "NO_RELEVANT_DOCUMENTS_FOUND"


@tool
def web_search(query: str) -> Dict:
    """
     Return top web search results for a given search query
     """
    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = tavily_client.search(query)
    return response


def summarize(state: State):
    # Summarize web search
    system_message = SystemMessage(
        "Summarize the search results from the web search tool into a "
        "coherent,"
        "helpful response, spanning 2-3 paragraphs."
        "Make sure to use at least 3 sources."
        "Cite your sources.")

    ai_message = llm.invoke(state["messages"] + [system_message])

    return {
        "messages": [ai_message],
        "summary": ai_message.content,
        "information_source": "rag"  # Add this line
    }


def ask_for_quiz(state: State):
    # This is a breakpoint to ask the user for input. Doesn't do anything else.
    return state


def route_to_quiz(state: State):
    # Checks the user's decision from the state and routes accordingly.
    if state.get("quiz_choice") == "yes":
        return "generate_quiz"
    else:
        # If they said no, ask if they want a new topic
        return "ask_for_new_topic"


def ask_for_new_topic(state: State):
    # This is a breakpoint to ask the user for input. Doesn't do anything else.
    return state


def route_to_new_topic(state: State):
    # Checks the user's decision and routes accordingly

    if state.get("new_topic_choice") == "yes":
        return "ask_topic_question"
    else:
        return "goodbye_message"


def goodbye_message(state: State):
    # Generate a friendly goodbye message

    farewell_content = ("👋 Thank you for using HealthBot! I hope the "
                        "information was helpful. Take care of your health, "
                        "and feel free to come back anytime you have more "
                        "health questions. Stay well! 🌟")

    # Create goodbye message
    goodbye_msg = AIMessage(content=farewell_content)

    return {
        "messages": [goodbye_msg],
        "information_source": None}


def ask_topic_question(state: State):
    # This is a breakpoint to ask for the new topic question
    return state


def generate_quiz(state: State):
    system_message = SystemMessage(
        "Generate a comprehension quiz based on the summary from the web "
        "search tool."
        "Only generate one single-sentence question and no options for "
        "answers, as the user is supposed to provide a free text answer."
        "Do not generate the correct answer yet."
        f'Use only this information as source for your question: '
        f'{state["summary"]}')
    ai_message = llm.invoke(state["messages"] + [system_message])

    return {"messages": [ai_message],
            "comprehension_question": ai_message.content}


def grade_quiz(state: State):
    system_message = SystemMessage(
        "You are grading a comprehension quiz about health"
        "Don't grade too hard - accept short answers from the user"
        f"The question was: {state['comprehension_question']}"
        f"The user's answer is: {state['quiz_answer']}"
        "Grade the user's answer with a grade from A (best) to F (failed)"
        f"For your grade, use only information from this summary of web "
        f"search results on the topic:{state['summary']}"
        "Provide a short explanation for your grade, and a citation from the "
        "summaries provided above")

    # Don't need the full message history here as we're only grading
    ai_message = llm.invoke([system_message])

    # Modify the message content by adding the congratulatory line at the start
    modified_content = (f"🎉 Well done! Here's how I grade your answer and an "
                        f"explanation:\n\n{ai_message.content}")

    # Create a new message with the modified content
    modified_message = AIMessage(content=modified_content)

    return {"messages": [modified_message]}


# bind tools
llm = llm.bind_tools([web_search, search_health_documents])

# build graph
workflow = StateGraph(State)
workflow.add_node("entry_point", entry_point)
workflow.add_node("agent", agent)
workflow.add_node("web_search", ToolNode([web_search]))
workflow.add_node("search_health_documents",
                  ToolNode([search_health_documents]))
workflow.add_node("agent_knowledge", agent_knowledge)
workflow.add_node("summarize", summarize)
workflow.add_node("generate_quiz", generate_quiz)
workflow.add_node("grade_quiz", grade_quiz)
workflow.add_node("ask_for_quiz", ask_for_quiz)
workflow.add_node("ask_for_new_topic", ask_for_new_topic)
workflow.add_node("ask_topic_question", ask_topic_question)
workflow.add_node("goodbye_message", goodbye_message)

# Start
workflow.add_edge(START, "entry_point")
workflow.add_edge("entry_point", "agent")

# Routes to web search tool
workflow.add_conditional_edges(source="agent", path=route_to_tool,
                               path_map=["search_health_documents", END])

# Route after RAG search - either to summarize or agent knowledge
workflow.add_conditional_edges(source="search_health_documents",
                               path=route_after_rag,
                               path_map={"summarize": "summarize",
                                         "agent_knowledge": "agent_knowledge"})

# Both summarize and agent_knowledge lead to quiz
workflow.add_edge("summarize", "ask_for_quiz")
workflow.add_edge("agent_knowledge", "ask_for_quiz")

# Check if they wanted a quiz and route
workflow.add_conditional_edges(source="ask_for_quiz", path=route_to_quiz,
                               path_map={"generate_quiz": "generate_quiz",
                                         "ask_for_new_topic":
                                             "ask_for_new_topic"})

workflow.add_edge("generate_quiz", "grade_quiz")

# At this point, we interrupt and ask if they want a new topic
workflow.add_edge("grade_quiz", "ask_for_new_topic")

# Route based on new topic choice
workflow.add_conditional_edges(source="ask_for_new_topic",
                               path=route_to_new_topic,
                               path_map={
                                   "ask_topic_question": "ask_topic_question",
                                   "goodbye_message": "goodbye_message"})

# Loop back to entry_point with the new question
workflow.add_edge("ask_topic_question", "entry_point")

# Add edge from goodbye to END:
workflow.add_edge("goodbye_message", END)

memory = MemorySaver()
graph = workflow.compile(
    interrupt_before=["ask_for_quiz", "ask_for_new_topic", "grade_quiz",
                      "ask_topic_question"], checkpointer=memory)

# Draw the graph for inspection/debugging
png_bytes = graph.get_graph().draw_mermaid_png()
with open("health_bot_workflow.png", "wb") as f:
    f.write(png_bytes)


class HealthBotSession:
    """
    Session-based health bot that processes one step at a time.
    The graph manages the flow, we just translate states to UI actions.
    """

    def __init__(self, initial_question: str):
        self.thread_id = str(uuid.uuid4())
        self.config = RunnableConfig()
        self.config["configurable"] = {"thread_id": self.thread_id}
        self.last_printed_message_id = None
        self.initial_question = initial_question

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
            for event in graph.stream(input=input_data, config=self.config,
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
            state = graph.get_state(self.config)
            next_node = state.next[0] if state.next else None

            if not next_node or next_node == END:
                return  # Conversation done

            # Yield appropriate input request and wait for user response
            if next_node == "ask_for_quiz":
                user_response = yield UserInputRequest(
                    prompt="Would you like to do a quiz about this topic?",
                    input_type="quiz_choice", options=["Yes", "No"])
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                graph.update_state(self.config, {"quiz_choice": choice})
                input_data = None  # No new input data needed, just continue

            elif next_node == "grade_quiz":
                user_response = yield UserInputRequest(
                    prompt="Please state your answer:",
                    input_type="quiz_answer")
                graph.update_state(self.config, {"quiz_answer": user_response})
                input_data = None

            elif next_node == "ask_for_new_topic":
                user_response = yield UserInputRequest(
                    prompt="Would you like to discuss another topic?",
                    input_type="new_topic_choice", options=["Yes", "No"])
                choice = "yes" if user_response.lower().strip() in ["y",
                                                                    "yes"] \
                    else "no"
                graph.update_state(self.config, {"new_topic_choice": choice})
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