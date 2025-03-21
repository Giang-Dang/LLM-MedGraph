"""
Database connection module for Neo4j interactions.
"""
import logging
from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, get_logger

# Get module-specific logger
logger = get_logger("db.connection")

# Initialize Neo4j driver as a global for reuse
_driver = None

def get_driver():
    """
    Get a Neo4j driver instance, creating it if it doesn't exist.
    
    Returns:
        neo4j.Driver: A reusable driver instance for database connections
    """
    global _driver
    if _driver is None:
        logger.info(f"Initializing Neo4j connection to {NEO4J_URI}")
        _driver = GraphDatabase.driver(
            NEO4J_URI, 
            auth=(NEO4J_USERNAME, NEO4J_PASSWORD)
        )
    return _driver

def close_driver():
    """Close the Neo4j driver if it exists."""
    global _driver
    if _driver is not None:
        logger.info("Closing Neo4j connection")
        _driver.close()
        _driver = None

def run_query(query, params=None):
    """
    Execute a Cypher query and return the results.
    
    Args:
        query (str): The Cypher query to execute
        params (dict, optional): Parameters for the query
        
    Returns:
        list: List of records returned by the query
    """
    driver = get_driver()
    with driver.session() as session:
        logger.debug(f"Executing query: {query}")
        result = session.run(query, params or {})
        return result.data()

def verify_entity_relationship(entity1, entity2):
    """
    Verify if there's a relationship between two entities in the Neo4j database.
    
    Args:
        entity1 (str): Name of the first entity
        entity2 (str): Name of the second entity
        
    Returns:
        bool: True if a relationship exists, False otherwise
    """
    driver = get_driver()
    with driver.session() as session:
        logger.debug(f"Verifying relationship between {entity1} and {entity2}")
        result = session.run(
            "MATCH (s)-[r]->(o) "
            "WHERE toLower(s.name) = toLower($entity1) AND toLower(o.name) = toLower($entity2) "
            "RETURN s, r, o",
            entity1=entity1,
            entity2=entity2
        )
        return result.single() is not None 