"""
Cypher query generator and executor module.
"""
import ollama
from ..config import LLM_MODEL, get_logger
from ..db.connection import run_query
from ..nlp.entity_extraction import analyze_question

# Get module-specific logger
logger = get_logger("query.cypher")

def generate_cypher_query(question):
    """
    Generate a Cypher query from a natural language question using LLM.
    
    Args:
        question (str): Natural language question about medical information
        
    Returns:
        tuple: (cypher_query, params) where cypher_query is the generated query string
               and params is a dictionary of parameters for the query
    """
    # Extract entities and query type using existing function
    entities, query_type = analyze_question(question)
    
    logger.info(f"Generating Cypher query for entities: {entities}, query type: {query_type}")
    
    # Create a schema description for the LLM
    schema_description = """
Schema:
- Nodes: Disease, Symptom, Treatment, Prevention, RiskFactor, AgeGroup, Gender
- Relationships:
  * (Disease)-[:HAS_SYMPTOM]->(Symptom)
  * (Disease)-[:HAS_TREATMENT]->(Treatment)
  * (Disease)-[:HAS_PREVENTION]->(Prevention)
  * (Disease)-[:HAS_RISK_FACTOR]->(RiskFactor)
  * (Disease)-[:AFFECTS]->(AgeGroup)
  * (Disease)-[:AFFECTS {prevalence: int}]->(Gender)
"""
    
    # Create examples for common query patterns
    examples = """
        Examples:
        1. "What are the symptoms of Influenza?"
        MATCH (d:Disease {name: 'Influenza'})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN d.name AS disease, collect(s.name) AS symptoms

        2. "Which diseases have Fever as a symptom?"
        MATCH (s:Symptom {name: 'Fever'})<-[:HAS_SYMPTOM]-(d:Disease)
        RETURN s.name AS symptom, collect(d.name) AS diseases

        3. "Which diseases have both Cough and Fever as symptoms?"
        MATCH (d:Disease)-[:HAS_SYMPTOM]->(s1:Symptom {name: 'Cough'})
        MATCH (d)-[:HAS_SYMPTOM]->(s2:Symptom {name: 'Fever'})
        RETURN collect(DISTINCT d.name) AS diseases, s1.name AS symptom1, s2.name AS symptom2

        4. "What treatments are available for Diabetes?"
        MATCH (d:Disease {name: 'Diabetes'})-[:HAS_TREATMENT]->(t:Treatment)
        RETURN d.name AS disease, collect(t.name) AS treatments

        5. "How does Migraine affect different genders?"
        MATCH (d:Disease {name: 'Migraine'})-[r:AFFECTS]->(g:Gender)
        RETURN d.name AS disease, collect({gender: g.name, prevalence: r.prevalence}) AS gender_prevalence
        
        6. "What prevention methods are available for Asthma?"
        MATCH (d:Disease {name: 'Asthma'})-[:HAS_PREVENTION]->(p:Prevention)
        RETURN d.name AS disease, collect(p.name) AS prevention_methods
        
        7. "Which diseases are prevented by Vaccination?"
        MATCH (p:Prevention {name: 'Vaccination'})<-[:HAS_PREVENTION]-(d:Disease)
        RETURN p.name AS prevention, collect(d.name) AS diseases
        
        8. "How many symptoms are linked to Influenza?"
        MATCH (d:Disease {name: 'Influenza'})-[:HAS_SYMPTOM]->(s:Symptom)
        RETURN d.name AS disease, count(s) AS symptom_count, collect(s.name) AS symptoms
    """

        # Create a prompt for the LLM
    prompt = f"""
        Given a medical question, generate a Neo4j Cypher query to answer it.

        {schema_description}

        {examples}

        User Question: "{question}"
        Query Type: {query_type}
        Extracted Entities: {', '.join(entities) if entities else 'None'}

        Return ONLY the Cypher query without any explanation or additional text. The query should be executable as-is in Neo4j.
    """

    try:
        # Get the Cypher query from the LLM
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt
        )
        
        # Extract the response text
        if hasattr(response, "response"):
            cypher_query = response.response.strip()
        elif hasattr(response, "text"):
            cypher_query = response.text.strip()
        else:
            cypher_query = str(response).strip()
        
        # Clean up the query (remove markdown code blocks if present)
        if cypher_query.startswith("```") and cypher_query.endswith("```"):
            cypher_query = cypher_query[3:-3].strip()
        if cypher_query.startswith("```cypher") or cypher_query.startswith("```Cypher"):
            cypher_query = cypher_query[9:].strip()
            if cypher_query.endswith("```"):
                cypher_query = cypher_query[:-3].strip()
                
        logger.info(f"Generated Cypher query for '{question}':\n{cypher_query}")
        
        # Prepare parameters
        params = {}
        for i, entity in enumerate(entities):
            params[f"entity{i}"] = entity
            # Replace placeholder parameters in the query
            if f"$entity{i}" not in cypher_query:
                # If the query doesn't use our parameter naming convention, add entity by name
                params[entity] = entity
        
        return cypher_query, params
        
    except Exception as e:
        logger.error(f"Error generating Cypher query: {str(e)}", exc_info=True)
        return None, {}


def execute_cypher_query(question):
    """
    Generate and execute a Cypher query from a natural language question.
    
    Args:
        question (str): Natural language question about medical information
        
    Returns:
        list: Results from the Neo4j query
    """
    cypher_query, params = generate_cypher_query(question)
    
    if not cypher_query:
        logger.warning("Failed to generate valid Cypher query")
        return "Failed to generate Cypher query"
    
    try:
        records = run_query(cypher_query, params)
        logger.debug(f"Query results: {records}")
            
        if not records:
            logger.info("Query executed successfully but returned no results")
            return "No results found."
            
        return records
            
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error executing Cypher query: {error_message}", exc_info=True)
        return f"Error: {error_message}\nQuery: {cypher_query}" 