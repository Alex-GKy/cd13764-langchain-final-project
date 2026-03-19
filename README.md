# Health Chatbot

A LangGraph-based chatbot for health information using RAG.

## Project Structure

- `src/health_chatbot/`: Core logic
  - `health_bot.py`: LangGraph definition
  - `health_rag_service.py`: RAG logic (using Haystack)
  - `app.py`: Streamlit UI
- `tests/`: Test scripts
- `langgraph.json`: Configuration for LangGraph server

## Setup

This project uses `uv` for dependency management.

1. Install `uv` if you haven't: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync`

## Running

### Using LangGraph Server (Dev Mode)

To run the agent with LangGraph server for development:

```bash
uv run langgraph dev
```

### Using Streamlit UI

To run the Streamlit application:

```bash
uv run streamlit run src/health_chatbot/app.py
```

## Testing

Run the test scripts in the `tests/` directory using `uv run`:

```bash
uv run python tests/HealthBotSessionTest.py
```
