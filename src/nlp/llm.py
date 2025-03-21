"""
LLM response generation module.
"""
import ollama
from ..config import LLM_MODEL, get_logger

# Get module-specific logger
logger = get_logger("nlp.llm")

def generate_response(question, use_graph=False, context=None):
    """
    Generate a response from the LLM, optionally using Neo4j for context.
    
    Args:
        question (str): The question to answer
        use_graph (bool): Whether to use graph-based context
        context (str or list, optional): Context data from Neo4j
        
    Returns:
        str: The generated response from the LLM
    """
    logger.info(f'Generating response for question: "{question}", using graph: {use_graph}')
    
    # If context is a list of dictionaries (from Neo4j), format it
    if isinstance(context, list):
        formatted_context = "Database results:\n"
        for item in context:
            formatted_context += str(item) + "\n"
        context = formatted_context
        logger.debug(f"Formatted context: {formatted_context}")
    
    # Create a prompt that includes the context if provided
    if use_graph and context:
        prompt = f"Question: {question}\n\nContext from medical database: {context}\n\nBased on the provided context, please answer the question."
        logger.debug("Using Neo4j context for response generation")
    else:
        prompt = question
        logger.debug("Using LLM's intrinsic knowledge (no graph context)")
    
    response = ollama.generate(
        model=LLM_MODEL,
        prompt=prompt
    )
    
    # Extract the response text
    if hasattr(response, "response"):
        return response.response
    elif hasattr(response, "text"):
        return response.text
    else:
        # Default fallback for any other format
        logger.warning("Unexpected response format from LLM")
        return str(response) 