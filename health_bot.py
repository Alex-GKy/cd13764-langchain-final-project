import os
from typing import Dict, Optional

import mlflow
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END, add_messages
from langgraph.prebuilt import ToolNode
from tavily import TavilyClient

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
llm = ChatOpenAI(model="gpt-4o-mini",
                 temperature=0.2,
                 base_url=base_url)


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
    # Routes to web search tool or falls back to agent knowledge
    last_message = state["messages"][-1]

    # TODO need to decide which tool use here
    if last_message.tool_calls:
        return "search_health_documents"
    else:
        # If no tool calls, use agent's general knowledge
        return "agent_knowledge"


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


def draw_workflow_diagram(compiled_graph, filename="health_bot_workflow.png"):
    """Draw the workflow diagram for inspection/debugging"""
    try:
        png_bytes = compiled_graph.get_graph().draw_mermaid_png()
        with open(filename, "wb") as f:
            f.write(png_bytes)
    except Exception as e:
        print(f"Could not generate workflow diagram: {e}")


def create_health_bot_graph(interrupt_before=None, checkpointer=None):
    """Factory function to create and return a configured health bot graph"""

    global llm

    if interrupt_before is None:
        interrupt_before = ["ask_for_quiz", "ask_for_new_topic", "grade_quiz",
                            "ask_topic_question"]

    if checkpointer is None:
        checkpointer = MemorySaver()

    # Bind tools to LLM
    llm = llm.bind_tools([web_search, search_health_documents])

    # Build workflow
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

    # Routes to web search tool or agent knowledge
    workflow.add_conditional_edges(source="agent", path=route_to_tool,
                                   path_map=["search_health_documents",
                                             "agent_knowledge"])

    # Route after RAG search - either to summarize or agent knowledge
    workflow.add_conditional_edges(source="search_health_documents",
                                   path=route_after_rag,
                                   path_map={"summarize": "summarize",
                                             "agent_knowledge":
                                                 "agent_knowledge"})

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
                                       "ask_topic_question":
                                           "ask_topic_question",
                                       "goodbye_message": "goodbye_message"})

    # Loop back to entry_point with the new question
    workflow.add_edge("ask_topic_question", "entry_point")

    # Add edge from goodbye to END:
    workflow.add_edge("goodbye_message", END)

    # Compile and return the graph
    compiled_graph = workflow.compile(
        interrupt_before=interrupt_before,
        checkpointer=checkpointer
    )

    return compiled_graph
