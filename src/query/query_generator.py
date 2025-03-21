"""
Query generator module for medical knowledge graph.
"""
import ollama
from neo4j import GraphDatabase
# Change relative imports to absolute imports
from src.db.connection import get_neo4j_session
from src.config import LLM_EVALUATION_MODEL, get_logger
import re

# Get module-specific logger
logger = get_logger("query.query_generator")

def generate_cypher_query(entities, query_type):
    """
    Generate a Cypher query to extract relevant medical information from the Neo4j database.
    
    Args:
        entities (list): List of entity names to query
        query_type (str): Type of information to extract (symptoms, treatments, etc.)
        
    Returns:
        str: A Cypher query string
    """
    logger.info(f"Generating Cypher query for entities: {entities}, query type: {query_type}")
    
    # If no entities are provided, use a reasonable default query
    if not entities or len(entities) == 0:
        logger.debug("No entities provided, using default query")
        return """
        MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN d.name AS disease, COLLECT(s.name) AS symptoms
        LIMIT 5
        """
    
    # Use LLM for more complex query generation
    query = create_query_with_llm(entities, query_type)
    
    if query:
        return query
    
    # Fallback to basic queries if LLM fails
    logger.debug("Falling back to template-based query generation")
    primary_entity = entities[0]
    
    if query_type == "symptoms":
        logger.debug(f"Generating symptoms query for {primary_entity}")
        return f"""
        MATCH (d:Disease {{name: '{primary_entity}'}})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN d.name AS disease, COLLECT(s.name) AS symptoms
        """
    elif query_type == "treatments":
        logger.debug(f"Generating treatments query for {primary_entity}")
        return f"""
        MATCH (d:Disease {{name: '{primary_entity}'}})-[:HAS_TREATMENT]->(t:Treatment)
        RETURN d.name AS disease, COLLECT(t.name) AS treatments
        """
    elif query_type == "prevention":
        logger.debug(f"Generating prevention query for {primary_entity}")
        return f"""
        MATCH (d:Disease {{name: '{primary_entity}'}})-[:HAS_PREVENTION]->(p:Prevention)
        RETURN d.name AS disease, COLLECT(p.name) AS preventions
        """
    elif query_type == "risk_factors":
        logger.debug(f"Generating risk factors query for {primary_entity}")
        return f"""
        MATCH (d:Disease {{name: '{primary_entity}'}})-[:HAS_RISK_FACTOR]->(r:RiskFactor)
        RETURN d.name AS disease, COLLECT(r.name) AS risk_factors
        """
    else:
        # Default general query
        logger.debug(f"Generating general query for {primary_entity}")
        return f"""
        MATCH (d:Disease {{name: '{primary_entity}'}})
        OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
        OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
        OPTIONAL MATCH (d)-[:HAS_PREVENTION]->(p:Prevention)
        RETURN d.name AS disease, 
               COLLECT(DISTINCT s.name) AS symptoms,
               COLLECT(DISTINCT t.name) AS treatments,
               COLLECT(DISTINCT p.name) AS preventions
        """

def create_query_with_llm(entities, query_type):
    """
    Use LLM to generate more complex and flexible Neo4j Cypher queries.
    
    Args:
        entities (list): List of entity names extracted from the question
        query_type (str): Type of query to generate
        
    Returns:
        str: A Cypher query string or None if generation fails
    """
    logger.debug(f"Attempting to create query with LLM for {query_type}")
    
    # Create a prompt that explains the database schema and asks for a relevant query
    schema_description = """
    The medical knowledge graph has these node types:
    - Disease: Medical conditions
    - Symptom: Disease symptoms 
    - Treatment: Medical treatments and therapies
    - Prevention: Preventive measures
    - RiskFactor: Factors that increase disease risk
    - AgeGroup: Age categories affected (Children, Adults, Elderly)
    - Gender: Gender categories (Male, Female)
    
    Key relationships in the graph:
    - (Disease)-[:HAS_SYMPTOM]->(Symptom)
    - (Disease)-[:HAS_TREATMENT]->(Treatment)
    - (Disease)-[:HAS_PREVENTION]->(Prevention)
    - (Disease)-[:HAS_RISK_FACTOR]->(RiskFactor)
    - (Disease)-[:AFFECTS]->(AgeGroup)
    - (Disease)-[:AFFECTS]->(Gender) with {prevalence} property
    """
    
    # Add additional context based on query type
    query_type_context = {
        "symptoms": "Focus on matching symptoms to diseases or finding symptom patterns",
        "treatments": "Focus on treatment options for specific diseases",
        "prevention": "Focus on preventive measures for diseases",
        "risk_factors": "Focus on risk factors associated with diseases",
        "age_groups": "Focus on how diseases affect different age groups",
        "gender": "Focus on gender distribution of diseases",
        "prevalence": "Focus on how common diseases are",
        "general": "Provide general information about the disease"
    }
    
    context = query_type_context.get(query_type, "Provide general information")
    
    # Construct the prompt for the LLM
    prompt = f"""
    Write a Neo4j Cypher query to answer a medical question.
    
    Database Schema:
    {schema_description}
    
    Entities mentioned: {', '.join(entities)}
    Query type: {query_type} - {context}
    
    IMPORTANT SYNTAX RULES:
    - Must verify that the query is valid before returning it
    - Always use RETURN at the end of the query
    - ALWAYS use toLower() for case-insensitive string comparisons like: WHERE toLower(d.name) = toLower("Hypertension")
    - When using IN for multiple values, use single quotes inside parentheses: WHERE toLower(s.name) IN ['fever', 'cough']
    - Never use multiple RETURN statements in a single query
    
    Generate a Cypher query that:
    1. Properly references the entities mentioned
    2. Returns the most relevant information for the query type
    3. Uses appropriate MATCH, WHERE, and RETURN clauses in the correct order
    4. Handles cases where data might not exist with OPTIONAL MATCH
    5. Includes relevant aggregation functions like COLLECT() where appropriate
    6. Limits results to relevant information only
    7. Match entities with their correct node types (e.g., use disease.name when comparing disease names, not symptom.name)
    
    EXAMPLES:
    
    BAD: MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) WHERE d.name = "hypertension" RETURN s.name AS SymptomName
    GOOD: MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) WHERE toLower(d.name) = toLower("hypertension") RETURN s.name AS SymptomName, r.name AS RelationshipName, d.name AS DiseaseName
    
    BAD: MATCH (s:Symptom)-[r:HAS_SYMPTOM]->(d:Disease) WHERE s.name = "Headache" RETURN d.name
    GOOD: MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) WHERE toLower(s.name) = toLower("Headache") RETURN s.name AS SymptomName, r.name AS RelationshipName, d.name AS DiseaseName
    
    BAD: MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) WHERE toLower(d.name) = toLower("Headache") RETURN s.name
    GOOD: MATCH (d:Disease)-[r:HAS_SYMPTOM]->(s:Symptom) WHERE toLower(s.name) = toLower("Headache") RETURN s.name AS SymptomName, r.name AS RelationshipName, d.name AS DiseaseName

    Return only the Cypher query with no explanation or markdown formatting.
    """
    
    try:
        # Call the LLM to generate the query
        logger.debug("Calling LLM for query generation")
        response = ollama.generate(
            model=LLM_EVALUATION_MODEL,
            prompt=prompt
        )
        
        # Extract the query from the response
        if hasattr(response, "response"):
            query = response.response.strip()
        elif hasattr(response, "text"):
            query = response.text.strip()
        else:
            query = str(response).strip()
        
        # Clean up the query - remove any markdown code formatting
        if "```" in query:
            query = query.split("```")[1].split("```")[0]
        
        # Remove any cypher or other language markers
        query = query.replace("cypher", "").strip()
        
        logger.info(f"Generated Cypher query with LLM ({LLM_EVALUATION_MODEL}): {query[:100]}...")
        
        return query
    
    except Exception as e:
        logger.error(f"Error generating query with LLM: {str(e)}")
        return None

def execute_query(query):
    """
    Execute a Cypher query against the Neo4j database.
    
    Args:
        query (str): The Cypher query to execute
        
    Returns:
        list: List of result records
    """
    results = []
    
    try:
        logger.info("Executing Neo4j query")
        logger.debug(f"Original query: {query}")
        
        logger.debug(f"Final query: {query}")
        session = get_neo4j_session()
        response = session.run(query)
        
        for record in response:
            # Convert record to a serializable dictionary
            record_dict = {}
            for key, value in dict(record).items():
                # Handle Neo4j specific types
                record_dict[key] = neo4j_to_python(value)
            results.append(record_dict)
        
        logger.info(f"Query returned {len(results)} results")
        logger.debug(f"Query results: {results}")
            
        session.close()
    except Exception as e:
        logger.error(f"Error executing Neo4j query: {str(e)}")
        # Return a structured error result for the frontend
        results = [{
            "error": str(e),
            "query": query
        }]
        
    return results

def neo4j_to_python(value):
    """
    Convert Neo4j types to Python native types for serialization.
    
    Args:
        value: A value from a Neo4j record
        
    Returns:
        A serializable Python object
    """
    from neo4j.graph import Node, Relationship, Path
    
    # Handle None
    if value is None:
        return None
        
    # Handle Neo4j Node
    if isinstance(value, Node):
        node_dict = dict(value)
        node_dict["_id"] = value.id
        node_dict["_labels"] = list(value.labels)
        return node_dict
        
    # Handle Neo4j Relationship
    if isinstance(value, Relationship):
        rel_dict = dict(value)
        rel_dict["_id"] = value.id
        rel_dict["_type"] = value.type
        rel_dict["_start_node"] = neo4j_to_python(value.start_node)
        rel_dict["_end_node"] = neo4j_to_python(value.end_node)
        return rel_dict
        
    # Handle Neo4j Path
    if isinstance(value, Path):
        return {
            "nodes": [neo4j_to_python(node) for node in value.nodes],
            "relationships": [neo4j_to_python(rel) for rel in value.relationships]
        }
        
    # Handle collections
    if isinstance(value, (list, set)):
        return [neo4j_to_python(item) for item in value]
        
    # Handle dictionaries
    if isinstance(value, dict):
        return {k: neo4j_to_python(v) for k, v in value.items()}
        
    # Pass through basic types
    return value 