"""
Configuration settings for the medical knowledge graph application.
Contains database connections, model settings, and other constants.
"""
import os
import logging
import logging.handlers
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FILENAME = os.getenv("LOG_FILENAME", f"medical_kg_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Create logs directory if it doesn't exist
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Create logger
logger = logging.getLogger("medical_kg")
logger.setLevel(getattr(logging, LOG_LEVEL))

# Clear any existing handlers (in case of module reload)
if logger.handlers:
    logger.handlers.clear()

# Configure console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

# Configure file handler
log_file_path = os.path.join(LOG_DIR, LOG_FILENAME)
file_handler = logging.handlers.RotatingFileHandler(
    log_file_path, 
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(getattr(logging, LOG_LEVEL))
file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)

logger.info(f"Logging configured. Log file: {log_file_path}")

def get_logger(module_name):
    """
    Get a logger for a specific module.
    
    Args:
        module_name (str): Name of the module requesting the logger
        
    Returns:
        logging.Logger: A logger instance with the specified name
    """
    return logging.getLogger(f"medical_kg.{module_name}")

# Neo4j connection settings
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# LLM model settings
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:4b")

# Entity types
ENTITY_TYPES = {
    "DISEASE": "Disease",
    "SYMPTOM": "Symptom",
    "TREATMENT": "Treatment",
    "PREVENTION": "Prevention",
    "RISK_FACTOR": "RiskFactor",
    "AGE_GROUP": "AgeGroup",
    "GENDER": "Gender"
}

# Relationship types
RELATIONSHIP_TYPES = {
    "HAS_SYMPTOM": "HAS_SYMPTOM",
    "HAS_TREATMENT": "HAS_TREATMENT",
    "HAS_PREVENTION": "HAS_PREVENTION",
    "HAS_RISK_FACTOR": "HAS_RISK_FACTOR",
    "AFFECTS": "AFFECTS"
}

# Query types
QUERY_TYPES = [
    "symptoms",      
    "treatments",    
    "prevention",    
    "risk_factors",  
    "age_groups",    
    "gender",        
    "prevalence",    
    "general"        
]

# Sample questions for evaluation
SAMPLE_QUESTIONS = [
    "What are the symptoms of Influenza?",
    "What treatments are available for Diabetes?",
    "What prevention methods are available for Asthma?",
    "What symptoms are associated with Hypertension?",
    "Which diseases have Fever as a symptom?",
    "What treatments does Migraine have?",
    "How can Influenza be prevented?",
    "List the symptoms of Diabetes.",
    "Find diseases that have Cough as a symptom.",
    "What prevention methods does Diabetes have?",
    "What is the treatment for Asthma?",
    "Which disease uses Vaccination as prevention?",
    "What symptoms does Asthma have?",
    "How many symptoms are linked to Influenza?",
    "Which diseases show Fatigue as a symptom?",
    "List all diseases with their symptoms.",
    "What is the prevention method for Migraine?",
    "What treatment is given for Hypertension?",
    "Find diseases that have Headache as a symptom.",
    "Which disease is linked to Nausea?",
    "List the treatments for Hypertension.",
    "What prevention methods are used for Influenza?",
    "What symptoms are related to Migraine?",
    "How is Diabetes treated?",
    "Which diseases are prevented by a Healthy Diet?",
    "List diseases that have Shortness of Breath as a symptom.",
    "What are the common symptoms of Asthma?",
    "Which diseases are linked to Cough and Fever?",
    "What treatment does Influenza have?",
    "What prevention is recommended for Hypertension?",
    "Which disease has the symptom Dizziness?",
    "List the treatments available for Migraine.",
    "What are the prevention methods for Diabetes?",
    "How many diseases have the symptom Chest Pain?",
    "Which diseases can be prevented by Regular Exercise?",
    "What symptom is most common in Influenza?",
    "Which diseases have Sweating as a symptom?"
] 