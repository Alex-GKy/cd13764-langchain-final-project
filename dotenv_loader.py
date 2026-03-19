from dotenv import load_dotenv
import os

load_dotenv(override=True)
openai_api_key = os.getenv("OPENAI_API_KEY")
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
