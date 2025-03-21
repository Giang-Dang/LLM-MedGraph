"""
Example usage of the Medical Knowledge Graph system.
This script provides simple examples of how to use the different components.
"""
from src.nlp.entity_extraction import extract_entities, analyze_question
from src.nlp.llm import generate_response
from src.query.cypher import execute_cypher_query
from src.evaluation.accuracy import evaluate_factual_accuracy
from src.db.connection import close_driver
from src.config import get_logger

# Get module-specific logger
logger = get_logger("example")

# Example 1: Extract entities from text
def example_entity_extraction():
    logger.info("Running entity extraction example")
    text = "What are the symptoms of Influenza?"
    
    # Display section header (user-facing)
    print("\n--- Example 1: Entity Extraction ---")
    
    entities = extract_entities(text)
    
    # Display results (user-facing)
    print(f"Entities extracted from '{text}':")
    for entity in entities:
        print(f"  - {entity['entity']} ({entity['label']})")
    
    # Analyze question to get entities and query type
    entities, query_type = analyze_question(text)
    logger.debug(f"Query type: {query_type}, Entities: {entities}")
    
    # Display results (user-facing)
    print(f"Query type: {query_type}")
    print(f"Entity names: {entities}")

# Example 2: Generate and execute a Cypher query
def example_cypher_query():
    logger.info("Running Cypher query example")
    question = "What treatments are available for Diabetes?"
    
    # Display section header (user-facing)
    print("\n--- Example 2: Cypher Query Generation ---")
    
    results = execute_cypher_query(question)
    logger.debug(f"Query results: {results}")
    
    # Display results (user-facing)
    print(f"Query results for '{question}':")
    print(results)

# Example 3: Generate responses with and without Neo4j
def example_response_generation():
    logger.info("Running response generation example")
    question = "What are the symptoms of Asthma?"
    
    # Display section header (user-facing)
    print("\n--- Example 3: Response Generation ---")
    
    # Without Neo4j context
    logger.info("Generating response without Neo4j context")
    print("Response without Neo4j:")
    response_without = generate_response(question, use_graph=False)
    print(response_without)
    
    # With Neo4j context
    logger.info("Generating response with Neo4j context")
    print("\nResponse with Neo4j:")
    context = execute_cypher_query(question)
    response_with = generate_response(question, use_graph=True, context=context)
    print(response_with)
    
    # Calculate accuracy
    logger.info("Calculating factual accuracy for both responses")
    print("\nFactual accuracy:")
    accuracy_without = evaluate_factual_accuracy(response_without)
    accuracy_with = evaluate_factual_accuracy(response_with)
    logger.debug(f"Accuracy without Neo4j: {accuracy_without:.2%}, with Neo4j: {accuracy_with:.2%}")
    
    # Display results (user-facing)
    print(f"Without Neo4j: {accuracy_without:.2%}")
    print(f"With Neo4j: {accuracy_with:.2%}")

if __name__ == "__main__":
    logger.info("Starting example script")
    try:
        example_entity_extraction()
        example_cypher_query()
        example_response_generation()
    finally:
        # Ensure the Neo4j driver is closed properly
        logger.debug("Closing Neo4j driver")
        close_driver()
    
    logger.info("Examples completed successfully")
    print("\nExamples completed.") 