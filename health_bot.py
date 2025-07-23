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
    quiz_choice: str
    new_topic_choice: str


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


def route_to_tool(state: State):
    last_message = state["messages"][-1]

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


def summarize(state: State):
    system_message = SystemMessage(
        "Summarize the search results from the web search tool into a "
        "coherent,"
        "helpful response, spanning 3-4 paragraphs."
        "Cite your sources."
    )
    ai_message = llm.invoke(state["messages"] + [system_message])
    return {"messages": [ai_message], "summary": ai_message.content}


def ask_for_quiz(state: State):
    # This is a breakpoint to ask the user for input

    return state


def route_to_quiz(state: State):
    """
    Checks the user's decision from the state and routes accordingly.
    This runs AFTER the human-in-the-loop step.
    """
    if state.get("quiz_choice") == "yes":
        return "generate_quiz"
    else:
        # If they said no, or if something went wrong, end the quiz flow.
        return END


def ask_for_new_topic(state: State):
    # This is a breakpoint to ask the user is they want to continue

    return state


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
workflow.add_node("ask_for_quiz", ask_for_quiz)
workflow.add_node("ask_for_new_topic", ask_for_new_topic)

# Start
workflow.add_edge(START, "entry_point")
workflow.add_edge("entry_point", "agent")

workflow.add_conditional_edges(
    source="agent",
    path=route_to_tool,
    path_map=["web_search", END]
)

workflow.add_edge("web_search", "summarize")
workflow.add_edge("summarize", "ask_for_quiz")

workflow.add_conditional_edges(
    source="ask_for_quiz",
    path=route_to_quiz,
    path_map={
        "generate_quiz": "generate_quiz",
        END: END
    }
)

workflow.add_edge("generate_quiz", "grade_quiz")
workflow.add_edge("grade_quiz", "ask_for_new_topic")

# This will interrupt so we can ask the user if they want to continue
workflow.add_edge("ask_for_new_topic", END)

memory = MemorySaver()
graph = workflow.compile(
    interrupt_before=["ask_for_quiz", "ask_for_new_topic", "grade_quiz"],
    checkpointer=memory)

# TODO remove before flight
# draw the graph for inspection reasons
png_bytes = graph.get_graph().draw_mermaid_png()
with open("health_bot_workflow.png", "wb") as f:
    f.write(png_bytes)


def hitl_health_bot(graph: CompiledStateGraph):
    # We'll start a new thread for each run of the graph
    thread_id = 0

    # Outer loop, each run is one separate conversation
    while True:

        thread_id += 1
        print(f"\n--- Starting new session (session ID: {thread_id}) ---\n")

        # Get a topic from the user and start the research
        user_question = input("\nWhat topic would you like to learn about?\n"
                              "> ")

        # Make sure they enter anything
        if not user_question.strip():
            print("OK, see you later then!")
            break

        # Not a must but for keeping types consistent
        config = RunnableConfig()
        config["configurable"] = {"thread_id": thread_id}

        # Need to keep track of which messages we're printing
        last_printed_message_id = None

        # This holds the input for the graph
        current_input = {"user_question": user_question}

        # This is the inner loop, representing one run of the graph
        # Basically, this keeps calling graph.stream and handles interrupts
        while True:
            for event in graph.stream(input=current_input,
                                      config=config,
                                      stream_mode="values"):
                if messages := event.get("messages", []):
                    message = messages[-1]

                    # Print the message only if it hasn't been yet
                    if message.id != last_printed_message_id:
                        message.pretty_print()
                        last_printed_message_id = message.id

            # As soon as an interrupt happens, check what's up next
            state = graph.get_state(config)
            next_node = state.next[0] if state.next else None

            # Check if we've reached the end
            if not state.next or state.next[0] == END:
                # print("\n--- See you later! ---\n")
                break

            # The graph is about to enter the quiz section - ask the user
            # if they're interested
            if next_node == "ask_for_quiz":
                # Start the quiz loop if the user wants to
                quiz_requested = input("Would you like to do a quiz? (y/n)\n"
                                       "> ")
                choice = "yes" if (quiz_requested.lower().strip()
                                   in ["y", "yes"]) else "no"

                graph.update_state(config, {"quiz_choice": choice})

            # Capture the answer to the quiz
            elif next_node == "grade_quiz":
                # Get the user's answer and make sure it's long enough
                quiz_answer = input("Please state your answer\n"
                                    "> ")
                while not quiz_answer.strip() or len(quiz_answer) < 5:
                    quiz_answer = input(
                        "It looks like you haven't entered an answer. Please "
                        "try again.\n"
                        "> ")

                graph.update_state(config, {"quiz_answer": quiz_answer})

            elif next_node == "ask_for_new_topic":
                new_topic_choice = input("Research another topic? (y/n)\n> ")
                choice = "yes" if new_topic_choice.lower().strip() in [
                    "y", "yes"] else "no"
                graph.update_state(config, {"new_topic_choice": choice})

            # After this, the inner loop will run again and continue the stream
            # Hence we need to make sure the graph's input will be empty
            current_input = None

        final_state = graph.get_state(config)
        if final_state.values.get("new_topic_choice") == "no":
            print("Got it, goodbye!")
            break


if __name__ == "__main__":
    hitl_health_bot(graph=graph)
