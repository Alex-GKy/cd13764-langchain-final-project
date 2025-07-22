from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph import StateGraph, MessagesState, START, END, add_messages
from langgraph.prebuilt import ToolNode
from tavily import TavilyClient
from typing import Dict
import os
import mlflow


# MLflow setup
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))
mlflow.set_experiment("health_bot")
mlflow.langchain.autolog()


# TODO remove before flight
# set up debug mode

from mock_responses import MOCK_WEB_SEARCH_RESPONSE

DEBUG = os.getenv("DEBUG")
base_url = "http://localhost:1234/v1" if DEBUG == "True" else \
    "https://openai.vocareum.com/v1"

# debug end
# TODO remove above

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.0,
    base_url=base_url
)


class State(MessagesState):
    user_question: str
    answer: str


def entry_point(state: State):
    print(state["user_question"])
    system_message = SystemMessage(
        "You are a health bot. You are a helpful and reliable assistant"
        " that answers questions about health."
        "You prefer to use web search to find information.When receiving "
        "search results,"
        "synthesize the information into a coherent, helpful response. Cite "
        "your sources."
    )

    human_message = HumanMessage(state["user_question"])
    messages = add_messages(system_message, human_message)

    return {"messages": messages}


def agent(state: State):
    ai_message = llm.invoke(state["messages"])
    return {"messages": [ai_message], "answer": ai_message.content}


def router(state: State):
    last_message = state["messages"][-1]

    # TODO handle multiple tool calls
    if last_message.tool_calls:
        return "web_search"
    else:
        return END


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

workflow.add_edge(START, "entry_point")
workflow.add_edge("entry_point", "agent")

workflow.add_conditional_edges(
    source="agent", path=router, path_map=["web_search", END]
)

workflow.add_edge("web_search", "agent")

memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# TODO remove before flight
# draw the graph for inspection reasons
png_bytes = graph.get_graph().draw_mermaid_png()
with open("health_bot_workflow.png", "wb") as f:
    f.write(png_bytes)


def hitl_health_bot(graph: CompiledStateGraph, thread_id: int):
    # TODO get input from user
    human_input = "Back pain"

    # not really needed but for keeping types consistent
    config = RunnableConfig()
    config["configurable"] = {"thread_id": thread_id}

    for event in graph.stream(input={"user_question": human_input},
                              config=config,
                              stream_mode="values"):
        if event.get("messages"):
            event["messages"][-1].pretty_print()


hitl_health_bot(graph=graph, thread_id=1)
