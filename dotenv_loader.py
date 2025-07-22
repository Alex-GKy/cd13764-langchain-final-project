from dotenv import load_dotenv
import os
from pathlib import Path

# Get the current working directory and go up one level
load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
