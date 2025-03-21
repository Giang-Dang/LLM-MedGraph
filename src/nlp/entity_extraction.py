"""
Entity extraction module for medical text processing.
"""
import json
import ollama
import medspacy
from medspacy.ner import TargetRule
from src.config import LLM_MODEL, get_logger

# Get module-specific logger
logger = get_logger("nlp.entity_extraction")

# Load NLP models
nlp = medspacy.load()
target_matcher = nlp.get_pipe("medspacy_target_matcher")

# Define disease rules
disease_rules = [
    TargetRule("Influenza", "DISEASE"),
    TargetRule("Diabetes", "DISEASE"),
    TargetRule("Hypertension", "DISEASE"),
    TargetRule("Asthma", "DISEASE"),
    TargetRule("Migraine", "DISEASE")
]

# Define symptoms
symptom_rules = [
    TargetRule("Fever", "SYMPTOM"),
    TargetRule("Cough", "SYMPTOM"),
    TargetRule("Fatigue", "SYMPTOM"),
    TargetRule("Shortness of Breath", "SYMPTOM"),
    TargetRule("Headache", "SYMPTOM"),
    TargetRule("Nausea", "SYMPTOM"),
    TargetRule("Dizziness", "SYMPTOM"),
    TargetRule("Chest Pain", "SYMPTOM"),
    TargetRule("Sweating", "SYMPTOM"),
    TargetRule("Blurred Vision", "SYMPTOM")
]

# Define preventions
prevention_rules = [
    TargetRule("Vaccination", "PREVENTION"),
    TargetRule("Healthy Diet", "PREVENTION"),
    TargetRule("Regular Exercise", "PREVENTION"),
    TargetRule("Avoid Allergens", "PREVENTION"),
    TargetRule("Stress Management", "PREVENTION")
]

# Define treatments
treatment_rules = [
    TargetRule("Antiviral Medication", "TREATMENT"),
    TargetRule("Insulin Therapy", "TREATMENT"),
    TargetRule("Antihypertensive Drugs", "TREATMENT"),
    TargetRule("Bronchodilators", "TREATMENT"),
    TargetRule("Pain Relievers", "TREATMENT")
]

# Add risk factors
risk_factor_rules = [
    TargetRule("Smoking", "RISK_FACTOR"),
    TargetRule("Obesity", "RISK_FACTOR"),
    TargetRule("High Salt Intake", "RISK_FACTOR"),
    TargetRule("Sedentary Lifestyle", "RISK_FACTOR"),
    TargetRule("Allergen Exposure", "RISK_FACTOR")
]

# Add age groups
age_group_rules = [
    TargetRule("Children", "AGE_GROUP"),
    TargetRule("Adults", "AGE_GROUP"),
    TargetRule("Elderly", "AGE_GROUP")
]

# Add genders
gender_rules = [
    TargetRule("Male", "GENDER"),
    TargetRule("Female", "GENDER")
]

# Combine all rules
all_rules = disease_rules + symptom_rules + prevention_rules + treatment_rules + risk_factor_rules + age_group_rules + gender_rules

# Add rules to the matcher
target_matcher.add(all_rules)

def extract_entities(text):
    """
    Extract medical entities from text using an LLM from Ollama.
    
    This function sends the input text to an LLM to identify medical entities
    such as diseases, symptoms, treatments, and more.
    
    Args:
        text (str): The text to extract entities from
        
    Returns:
        list: A list of dictionaries containing entity name and type, in format {'entity': 'name', 'label': 'TYPE'}
    """
    prompt = f"""
    Extract all medical entities from the following text and classify them by type.
    
    Text: "{text}"
    
    Extract entities of these types:
    - DISEASE (e.g., Influenza, Diabetes, Asthma)
    - SYMPTOM (e.g., Fever, Cough, Headache)
    - TREATMENT (e.g., Insulin Therapy, Pain Relievers)
    - PREVENTION (e.g., Vaccination, Regular Exercise)
    - RISK_FACTOR (e.g., Smoking, Obesity)
    - AGE_GROUP (e.g., Children, Adults, Elderly)
    - GENDER (e.g., Male, Female)
    
    Format your response as a JSON array with objects containing 'entity' and 'label' fields:
    [
      {{"entity": "Disease Name", "label": "DISEASE"}},
      {{"entity": "Symptom Name", "label": "SYMPTOM"}},
      ...
    ]
    
    Return ONLY the JSON array, nothing else.
    """
    
    try:
        # Call Ollama LLM
        logger.debug(f"Extracting entities from text: {text[:50]}...")
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt
        )
        
        # Extract the response text
        if hasattr(response, "response"):
            llm_response = response.response.strip()
        elif hasattr(response, "text"):
            llm_response = response.text.strip()
        else:
            llm_response = str(response).strip()
        
        # Clean up the response to extract just the JSON part
        if "```json" in llm_response:
            json_part = llm_response.split("```json")[1].split("```")[0].strip()
            llm_response = json_part
        elif "```" in llm_response:
            json_part = llm_response.split("```")[1].split("```")[0].strip()
            llm_response = json_part
        
        entities = json.loads(llm_response)
        
        formatted_entities = []
        for entity in entities:
            if isinstance(entity, dict) and 'entity' in entity and 'label' in entity:
                formatted_entities.append({
                    'entity': entity['entity'],
                    'label': entity['label']
                })
        
        logger.info(f"Extracted {len(formatted_entities)} entities from text")
        logger.debug(f"Extracted entities: {formatted_entities}")
        return formatted_entities
        
    except Exception as e:
        logger.error(f"Error extracting entities with LLM: {str(e)}")
        # Fall back to rule-based extraction if LLM fails
        return []


def analyze_question(question):
    """
    Analyze the question to identify entities and determine the type of medical information requested.
    Uses LLM to classify the query type instead of hardcoded keyword matching.
    
    Args:
        question (str): The medical question to analyze
        
    Returns:
        tuple: (entities, query_type) where entities is a list of entity names and
              query_type is the classified type of question
    """
    logger.info(f"Analyzing question: {question}")
    entities_data = extract_entities(question.lower())
    entities = [entity['entity'] for entity in entities_data]
    
    # If no entities were detected, try to manually extract common medical terms
    if len(entities) == 0:
        logger.debug("No entities detected, trying manual extraction")
        # Check for common symptoms that might not be detected as entities
        common_symptoms = ["fever", "cough", "fatigue", "headache", "nausea", "dizziness", 
                          "chest pain", "shortness of breath", "sweating", "blurred vision"]
        
        found_symptoms = []
        for symptom in common_symptoms:
            if symptom.lower() in question.lower():
                found_symptoms.append(symptom.title())
                
        if found_symptoms:
            entities = found_symptoms
            logger.info(f"Manually extracted symptoms: {found_symptoms}")
    
    # Use LLM to determine the query type
    prompt = f"""
        Given the following medical question: "{question}"

        Classify the type of information being requested into ONE of these categories:
        1. symptoms - Questions about symptoms of a disease or diseases that have certain symptoms
        2. treatments - Questions about treatments for a disease or diseases treated by specific methods
        3. prevention - Questions about how to prevent a disease or diseases prevented by specific methods
        4. risk_factors - Questions about risk factors for a disease
        5. age_groups - Questions about which age groups are affected by a disease
        6. gender - Questions about gender distribution of a disease
        7. prevalence - Questions about how common a disease is
        8. general - General questions about a disease that don't fit other categories

        Respond with ONLY the category name, nothing else.
    """
    
    # Get the query type from the LLM
    try:
        logger.debug("Classifying query type with LLM")
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt
        )
        
        # Extract the response text
        if hasattr(response, "response"):
            llm_query_type = response.response.strip().lower()
        elif hasattr(response, "text"):
            llm_query_type = response.text.strip().lower()
        else:
            llm_query_type = str(response).strip().lower()
        
        # Make sure the result is a valid query type
        from src.config import QUERY_TYPES
        if llm_query_type in QUERY_TYPES:
            query_type = llm_query_type
        else:
            # Default to general if the LLM response isn't a valid query type
            query_type = "general"
            logger.warning(f"LLM returned invalid query type: {llm_query_type}, defaulting to 'general'")
            
        logger.info(f"Question classified as query type: {query_type}")
    
    except Exception as e:
        logger.error(f"Error using LLM to classify query type: {str(e)}")
        
        # Fallback to simplified keyword matching if LLM fails
        simplified_keywords = {
            "symptom": "symptoms",
            "treatment": "treatments",
            "prevent": "prevention",
            "risk": "risk_factors",
            "age": "age_groups", 
            "gender": "gender",
            "common": "prevalence"
        }
        
        query_type = "general"
        for keyword, q_type in simplified_keywords.items():
            if keyword in question.lower():
                query_type = q_type
                break
                
        logger.info(f"Fallback classification for '{question}': {query_type}")
    
    return entities, query_type 