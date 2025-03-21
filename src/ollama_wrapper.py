import ollama
from config import OLLAMA_MODEL


def generate_response(prompt):
    """Generate response using the module-level generate function from ollama."""
    return ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )
