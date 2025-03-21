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

# Application constants
APPLICATION_NAME = "Medical Knowledge Graph"
EVALUATION_METHODS = ["standard", "detailed", "comprehensive"]
DEFAULT_REPORT_FILENAME = f"evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

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

EXPECTED_QA_PAIRS = [
    {
        "question": "What are the symptoms of Influenza?",
        "expected_answer": "The symptoms of Influenza are fever, cough, and fatigue."
    },
    {
        "question": "What treatments are available for Diabetes?",
        "expected_answer": "Diabetes is treated with insulin therapy."
    },
    {
        "question": "What prevention methods are available for Asthma?",
        "expected_answer": "Asthma can be prevented by avoiding allergens."
    },
    {
        "question": "What symptoms are associated with Hypertension?",
        "expected_answer": "Hypertension is associated with shortness of breath and chest pain."
    },
    {
        "question": "Which diseases have Fever as a symptom?",
        "expected_answer": "Influenza has fever as a symptom."
    },
    {
        "question": "What treatments does Migraine have?",
        "expected_answer": "Migraines are treated with pain relievers."
    },
    {
        "question": "How can Influenza be prevented?",
        "expected_answer": "Influenza can be prevented through vaccination."
    },
    {
        "question": "List the symptoms of Diabetes.",
        "expected_answer": "Diabetes has symptoms of fatigue and blurred vision."
    },
    {
        "question": "Find diseases that have Cough as a symptom.",
        "expected_answer": "Influenza and Asthma have cough as a symptom."
    },
    {
        "question": "What prevention methods does Diabetes have?",
        "expected_answer": "Diabetes can be prevented with a healthy diet."
    },
    {
        "question": "What is the treatment for Asthma?",
        "expected_answer": "Asthma is treated with bronchodilators."
    },
    {
        "question": "Which disease uses Vaccination as prevention?",
        "expected_answer": "Influenza uses vaccination as prevention."
    },
    {
        "question": "What symptoms does Asthma have?",
        "expected_answer": "Asthma has symptoms of shortness of breath and cough."
    },
    {
        "question": "How many symptoms are linked to Influenza?",
        "expected_answer": "Influenza has 3 symptoms: fever, cough, and fatigue."
    },
    {
        "question": "Which diseases show Fatigue as a symptom?",
        "expected_answer": "Influenza and Diabetes show fatigue as a symptom."
    },
    {
        "question": "List all diseases with their symptoms.",
        "expected_answer": "Influenza: fever, cough, fatigue. Diabetes: fatigue, blurred vision. Hypertension: shortness of breath, chest pain. Asthma: shortness of breath, cough. Migraine: headache, nausea."
    },
    {
        "question": "What is the prevention method for Migraine?",
        "expected_answer": "Migraines can be prevented through stress management."
    },
    {
        "question": "What treatment is given for Hypertension?",
        "expected_answer": "Hypertension is treated with antihypertensive drugs."
    },
    {
        "question": "Find diseases that have Headache as a symptom.",
        "expected_answer": "Migraine has headache as a symptom."
    },
    {
        "question": "Which disease is linked to Nausea?",
        "expected_answer": "Migraine is linked to nausea."
    },
    {
        "question": "List the treatments for Hypertension.",
        "expected_answer": "Hypertension is treated with antihypertensive drugs."
    },
    {
        "question": "What prevention methods are used for Influenza?",
        "expected_answer": "Influenza prevention includes vaccination."
    },
    {
        "question": "What symptoms are related to Migraine?",
        "expected_answer": "Migraines are related to headaches and nausea."
    },
    {
        "question": "How is Diabetes treated?",
        "expected_answer": "Diabetes is treated with insulin therapy."
    },
    {
        "question": "Which diseases are prevented by a Healthy Diet?",
        "expected_answer": "Diabetes is prevented by a healthy diet."
    },
    {
        "question": "List diseases that have Shortness of Breath as a symptom.",
        "expected_answer": "Hypertension and Asthma have shortness of breath as a symptom."
    },
    {
        "question": "What are the common symptoms of Asthma?",
        "expected_answer": "Asthma has symptoms of shortness of breath and cough."
    },
    {
        "question": "Which diseases are linked to Cough and Fever?",
        "expected_answer": "Influenza is linked to both cough and fever."
    },
    {
        "question": "What treatment does Influenza have?",
        "expected_answer": "Influenza is treated with antiviral medication."
    },
    {
        "question": "What prevention is recommended for Hypertension?",
        "expected_answer": "Regular exercise is recommended for preventing hypertension."
    },
    {
        "question": "Which disease has the symptom Dizziness?",
        "expected_answer": "None of the diseases in the database have dizziness as a symptom."
    },
    {
        "question": "List the treatments available for Migraine.",
        "expected_answer": "Migraines are treated with pain relievers."
    },
    {
        "question": "What are the prevention methods for Diabetes?",
        "expected_answer": "Diabetes can be prevented with a healthy diet."
    },
    {
        "question": "How many diseases have the symptom Chest Pain?",
        "expected_answer": "One disease (Hypertension) has chest pain as a symptom."
    },
    {
        "question": "Which diseases can be prevented by Regular Exercise?",
        "expected_answer": "Hypertension can be prevented by regular exercise."
    },
    {
        "question": "What symptom is most common in Influenza?",
        "expected_answer": "According to the prevalence data, fever is the most common symptom in Influenza with a prevalence of 90."
    },
    {
        "question": "Which diseases have Sweating as a symptom?",
        "expected_answer": "None of the diseases in the database have sweating as a symptom."
    }
] 