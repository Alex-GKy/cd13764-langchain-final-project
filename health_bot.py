from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph import StateGraph, MessagesState, START, END, add_messages
from langgraph.prebuilt import ToolNode
from tavily import TavilyClient
from typing import Dict
import dotenv_loader
import os
import mlflow

# MLFlow setup
try:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI",
                                      "http://127.0.0.1:5000"))
    mlflow.set_experiment("health_bot")
    mlflow.langchain.autolog()
except:
    print("MLflow server not running. Proceeding without MLflow.")

# TODO remove before flight
# set up debug mode

from mock_responses import MOCK_WEB_SEARCH_RESPONSE

DEBUG = os.getenv("DEBUG")
base_url = "http://localhost:1234/v1" if DEBUG == "True" else \
    "https://openai.vocareum.com/v1"

print(f"Debug: {DEBUG}, \n"
      f"base_url: {base_url}")

# debug end
# TODO remove above

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
    base_url=base_url
)


class State(MessagesState):
    user_question: str
    summary: str
    comprehension_question: str
    quiz_answer: str


def entry_point(state: State):
    print(state["user_question"])
    system_message = SystemMessage(
        "You are a health bot. You are a helpful and reliable assistant"
        " that answers questions about health."
        "You prefer to use web search to find information. When receiving "
        "a question, use web search to find top web search results"
    )

    human_message = HumanMessage(state["user_question"])
    messages = add_messages(system_message, human_message)

    return {"messages": messages}


def agent(state: State):
    ai_message = llm.invoke(state["messages"])
    return {"messages": [ai_message]}


def router(state: State):
    last_message = state["messages"][-1]

    # TODO handle multiple tool calls
    if last_message.tool_calls:
        return "web_search"
    else:
        return END


def summarize(state: State):
    system_message = SystemMessage(
        "Summarize the search results from the web search tool into a "
        "coherent,"
        "helpful response, spanning 3-4 paragraphs."
        "Cite your sources."
    )
    ai_message = llm.invoke(state["messages"] + [system_message])
    return {"messages": [ai_message], "summary": ai_message.content}


def generate_quiz(state: State):
    system_message = SystemMessage(
        "Generate a comprehension quiz based on the summary from the web "
        "search tool."
        "Only generate one single-sentence question and no options for "
        "answers, as the user is supposed to provide a free text answer."
        "Do not generate the correct answer yet."
        f'Use only this information as source for your question: '
        f'{state["summary"]}'
    )
    ai_message = llm.invoke(state["messages"] + [system_message])

    # TODO remove before flight - local LLM can't handle this
    if DEBUG == "True":
        ai_message = AIMessage(
            content="Here is a sample question: What causes back pain?\n",
            metadata={}
        )

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
        "summaries provided above"
    )

    # Don't need full context here as we're only grading
    ai_message = llm.invoke([system_message])

    return {"messages": [ai_message]}


@tool
def web_search(query: str) -> Dict:
    """
     Return top web search results for a given search query
     """
    if DEBUG == "True":
        return MOCK_WEB_SEARCH_RESPONSE

    tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = tavily_client.search(query)
    return response


# bind tools
llm = llm.bind_tools([web_search])

# build graph
workflow = StateGraph(State)
workflow.add_node("entry_point", entry_point)
workflow.add_node("agent", agent)
workflow.add_node("web_search", ToolNode([web_search]))
workflow.add_node("summarize", summarize)
workflow.add_node("generate_quiz", generate_quiz)
workflow.add_node("grade_quiz", grade_quiz)

workflow.add_edge(START, "entry_point")
workflow.add_edge("entry_point", "agent")

workflow.add_conditional_edges(
    source="agent", path=router, path_map=["web_search", END]
)

workflow.add_edge("web_search", "summarize")
workflow.add_edge("summarize", "generate_quiz")
workflow.add_edge("generate_quiz", "grade_quiz")
workflow.add_edge("grade_quiz", END)

memory = MemorySaver()
graph = workflow.compile(
    interrupt_after=["summarize", "generate_quiz", "grade_quiz"],
    checkpointer=memory)

# TODO remove before flight
# draw the graph for inspection reasons
png_bytes = graph.get_graph().draw_mermaid_png()
with open("health_bot_workflow.png", "wb") as f:
    f.write(png_bytes)


def hitl_health_bot(graph: CompiledStateGraph):
    thread_id = 0
    while True:
        thread_id += 1
        print(f"\n--- Starting new session (session ID: {thread_id}) ---")
        # TODO get input from user
        user_question = "Back pain"

        # not really needed but for keeping types consistent
        config = RunnableConfig()
        config["configurable"] = {"thread_id": thread_id}

        for event in graph.stream(input={"user_question": user_question},
                                  config=config,
                                  stream_mode="values"):
            if event.get("messages"):
                event["messages"][-1].pretty_print()

        # TODO get input from user
        # quiz_requested = input("Would you like to do a comprehension quiz? (
        # y/n)")
        quiz_requested = "yes"
        if quiz_requested.lower() in ["yes", "y"]:

            # TODO this prints the last message again, leading to a
            #  duplicate print
            for event in graph.stream(input=None, config=config,
                                      stream_mode="values"):
                if event.get("messages"):
                    event["messages"][-1].pretty_print()

        # TODO get input from user, handle cases where they won't provide
        #  an answer

        # quiz_answer = input("What's the answer to this question (free
        # text)?")
        quiz_answer = (
            "Symptoms for back pain are pain, of course. Causes: Bad posture, "
            "long sitting, too fat or no exercise")

        graph.update_state(config, {"quiz_answer": quiz_answer})

        for event in graph.stream(input=None,
                                  config=config,
                                  stream_mode="values"):
            if event.get("messages"):
                event["messages"][-1].pretty_print()

        # TODO get user input
        user_proceeds = "n"
        if user_proceeds.lower() not in ["yes", "y"]:
            print("\nExiting.")
            break


if __name__ == "__main__":
    hitl_health_bot(graph=graph)
