from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from the .env file

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

OLLAMA_MODEL = "deepseek-r1:14b"

SPACY_MODEL = "en_core_web_sm"
