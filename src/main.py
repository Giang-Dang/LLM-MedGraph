from neo4j import GraphDatabase
import ollama
import medspacy
from medspacy.ner import TargetMatcher, TargetRule
from datetime import datetime
import json

# Initialize Neo4j driver
neo4j_uri = "bolt://localhost:7687"
neo4j_username = "neo4j"
neo4j_password = "12345678"
driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))

# Load NLP models
nlp = medspacy.load()
target_matcher = nlp.get_pipe("medspacy_target_matcher")

# Define diseases
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


# def extract_medical_entities(text):
#     """Extract medical entities from text using medspaCy."""
#     doc = nlp(text.lower())
#     entities = []
#     for ent in doc.ents:
#         entities.append({
#             'entity': ent.text,
#             'label': ent.label_
#         })
#     print(f'extract_medical_entities > results for {text} : {entities}')
#     return entities

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
        response = ollama.generate(
            model="gemma3:4b",
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
        
        print(f'extract_entities_with_llm > results for {text}: {formatted_entities}')
        return formatted_entities
        
    except Exception as e:
        print(f"Error extracting entities with LLM: {str(e)}")
        # Fall back to rule-based extraction if LLM fails
        return []


def verify_entity_relationship(entity1, entity2):
    """Verify if there's a relationship between two entities in the Neo4j database."""
    with driver.session() as session:
        result = session.run(
            "MATCH (s)-[r]->(o) "
            "WHERE toLower(s.name) = toLower($entity1) AND toLower(o.name) = toLower($entity2) "
            "RETURN s, r, o",
            entity1=entity1,
            entity2=entity2
        )
        return result.single() is not None


def analyze_question(question):
    """
    Analyze the question to identify entities and determine the type of medical information requested.
    Uses LLM to classify the query type instead of hardcoded keyword matching.
    """
    entities_data = extract_entities(question.lower())
    entities = [entity['entity'] for entity in entities_data]
    
    query_types = [
        "symptoms",      
        "treatments",    
        "prevention",    
        "risk_factors",  
        "age_groups",    
        "gender",        
        "prevalence",    
        "general"        
    ]
    
    # If no entities were detected, try to manually extract common medical terms
    if len(entities) == 0:
        # Check for common symptoms that might not be detected as entities
        common_symptoms = ["fever", "cough", "fatigue", "headache", "nausea", "dizziness", 
                          "chest pain", "shortness of breath", "sweating", "blurred vision"]
        
        found_symptoms = []
        for symptom in common_symptoms:
            if symptom.lower() in question.lower():
                found_symptoms.append(symptom.title())
                
        if found_symptoms:
            entities = found_symptoms
    
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
        response = ollama.generate(
            model="gemma3:4b",
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
        if llm_query_type in query_types:
            query_type = llm_query_type
        else:
            # Default to general if the LLM response isn't a valid query type
            query_type = "general"
            
        print(f"LLM classified the question '{question}' as query type: {query_type}")
    
    except Exception as e:
        print(f"Error using LLM to classify query type: {str(e)}")
        
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
                
        print(f"Fallback classification for '{question}': {query_type}")
    
    # Check if this is a reverse lookup (asking about diseases related to properties)
    reverse_lookup_keywords = [
        "which disease", "what disease", "which diseases", "what diseases", 
        "list diseases", "find diseases", "diseases that have", "diseases with", 
        "diseases associated", "disease is linked", "diseases are linked", 
        "disease has", "diseases have", "linked to"
    ]
    
    is_reverse_lookup = any(keyword in question.lower() for keyword in reverse_lookup_keywords)
    if is_reverse_lookup:
        print(f"Detected reverse lookup query: '{question}'")

    return entities, query_type


# def fetch_context_from_neo4j(entities, query_type):
#     """
#     Fetch relevant context from Neo4j based on entities and query type.
    
#     This function handles four types of lookups:
#     1. Forward lookups (disease → property)
#     2. Reverse lookups (property → disease)
#     3. List all queries (showing all relationships of a specific type)
#     4. Multi-entity lookups (finding diseases related to multiple symptoms/treatments/etc.)
    
#     Args:
#         entities (list): List of entity names extracted from the question
#         query_type (str): Type of information being requested (symptoms, treatments, etc.)
        
#     Returns:
#         str: Formatted context text containing relevant medical information
#     """
#     context = ""
    
#     # Handle "list all" type queries when no specific entities are provided
#     if len(entities) == 0:
#         context = _handle_list_all_query(query_type)
#         if context:
#             return context
    
#     # Maps for node types, relationships, and display names
#     query_type_mapping = {
#         "symptoms": {"node": "Symptom", "relationship": "HAS_SYMPTOM", "display": "symptoms"},
#         "treatments": {"node": "Treatment", "relationship": "HAS_TREATMENT", "display": "treatments"},
#         "prevention": {"node": "Prevention", "relationship": "HAS_PREVENTION", "display": "prevention methods"},
#         "risk_factors": {"node": "RiskFactor", "relationship": "HAS_RISK_FACTOR", "display": "risk factors"},
#         "age_groups": {"node": "AgeGroup", "relationship": "AFFECTS", "display": "age groups"},
#         "gender": {"node": "Gender", "relationship": "AFFECTS", "display": "genders"}
#     }
    
#     # Check if this is a multi-entity reverse lookup
#     if query_type in query_type_mapping and len(entities) > 1:
#         # Count entity types to determine if this is a reverse lookup
#         with driver.session() as session:
#             entity_count = 0
#             disease_count = 0
            
#             # For each entity, check if it's a disease or the expected entity type
#             for entity in entities:
#                 # Check if entity is of the expected type for this query
#                 result = session.run(
#                     f"MATCH (e:{query_type_mapping[query_type]['node']}) WHERE toLower(e.name) = toLower($entity) RETURN count(e) AS count",
#                     entity=entity
#                 )
#                 record = result.single()
#                 if record and record["count"] > 0:
#                     entity_count += 1
                
#                 # Check if entity is a disease
#                 result = session.run(
#                     "MATCH (d:Disease) WHERE toLower(d.name) = toLower($entity) RETURN count(d) AS count",
#                     entity=entity
#                 )
#                 record = result.single()
#                 if record and record["count"] > 0:
#                     disease_count += 1
            
#             # If we have more of the expected entity type than diseases, assume it's a reverse lookup
#             if entity_count > disease_count:
#                 # Collect confirmed entities of the expected type
#                 confirmed_entities = []
#                 for entity in entities:
#                     result = session.run(
#                         f"MATCH (e:{query_type_mapping[query_type]['node']}) WHERE toLower(e.name) = toLower($entity) RETURN e.name AS name",
#                         entity=entity
#                     )
#                     record = result.single()
#                     if record:
#                         confirmed_entities.append(record["name"])
                
#                 if confirmed_entities:
#                     return _execute_multi_entity_lookup(
#                         confirmed_entities,
#                         query_type_mapping[query_type]["node"],
#                         query_type_mapping[query_type]["relationship"],
#                         query_type_mapping[query_type]["display"]
#                     )
    
#     # Process each entity from the question
#     for entity in entities:
#         # Try forward lookup first (disease → properties)
#         forward_result = _execute_forward_lookup(entity, query_type)
#         if forward_result:
#             context += forward_result
#             continue
            
#         # If forward lookup fails, try reverse lookup (property → diseases)
#         reverse_result = _execute_reverse_lookup(entity, query_type)
#         if reverse_result:
#             context += reverse_result
    
#     return context


# def _handle_list_all_query(query_type):
#     """
#     Handle queries that request information about all relationships of a certain type.
    
#     Args:
#         query_type (str): Type of medical information requested
        
#     Returns:
#         str: Formatted context with information about all entities of the requested type
#     """
#     # Define templates for listing all relationships
#     list_all_templates = {
#         "symptoms": """
#             MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
#             RETURN collect(DISTINCT {disease: d.name, symptoms: collect(s.name)}) AS disease_symptoms
#         """,
#         "treatments": """
#             MATCH (d:Disease)-[:HAS_TREATMENT]->(t:Treatment)
#             RETURN collect(DISTINCT {disease: d.name, treatments: collect(t.name)}) AS disease_treatments
#         """,
#         "prevention": """
#             MATCH (d:Disease)-[:HAS_PREVENTION]->(p:Prevention)
#             RETURN collect(DISTINCT {disease: d.name, prevention_methods: collect(p.name)}) AS disease_prevention
#         """,
#         "risk_factors": """
#             MATCH (d:Disease)-[:HAS_RISK_FACTOR]->(r:RiskFactor)
#             RETURN collect(DISTINCT {disease: d.name, risk_factors: collect(r.name)}) AS disease_risk_factors
#         """
#     }
    
#     # Return early if this query type doesn't support list all
#     if query_type not in list_all_templates:
#         return ""
        
#     context = ""
#     with driver.session() as session:
#         try:
#             result = session.run(list_all_templates[query_type])
#             record = result.single()
            
#             if not record:
#                 return ""
                
#             context += f"## {query_type.title()} for all diseases:\n\n"
            
#             if query_type == "symptoms":
#                 for item in record["disease_symptoms"]:
#                     context += f"Disease: {item['disease']}\nSymptoms: {', '.join(item['symptoms'])}\n\n"
#             elif query_type == "treatments":
#                 for item in record["disease_treatments"]:
#                     context += f"Disease: {item['disease']}\nTreatments: {', '.join(item['treatments'])}\n\n"
#             elif query_type == "prevention":
#                 for item in record["disease_prevention"]:
#                     context += f"Disease: {item['disease']}\nPrevention Methods: {', '.join(item['prevention_methods'])}\n\n"
#             elif query_type == "risk_factors":
#                 for item in record["disease_risk_factors"]:
#                     context += f"Disease: {item['disease']}\nRisk Factors: {', '.join(item['risk_factors'])}\n\n"
#         except Exception as e:
#             print(f"Error executing list all query for {query_type}: {str(e)}")
            
#     return context


# def _execute_forward_lookup(entity, query_type):
#     """
#     Execute a forward lookup query (disease → property).
    
#     Args:
#         entity (str): Entity name to look up
#         query_type (str): Type of information being requested
        
#     Returns:
#         str: Formatted context text or empty string if no results
#     """
#     # Forward lookup templates (disease → property)
#     forward_query_templates = {
#         "symptoms": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
#             RETURN d.name AS disease, collect(s.name) AS symptoms
#         """,
#         "treatments": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
#             RETURN d.name AS disease, collect(t.name) AS treatments
#         """,
#         "prevention": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[:HAS_PREVENTION]->(p:Prevention)
#             RETURN d.name AS disease, collect(p.name) AS prevention_methods
#         """,
#         "risk_factors": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[:HAS_RISK_FACTOR]->(r:RiskFactor)
#             RETURN d.name AS disease, collect(r.name) AS risk_factors
#         """,
#         "age_groups": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[:AFFECTS]->(a:AgeGroup)
#             RETURN d.name AS disease, collect(a.name) AS age_groups
#         """,
#         "gender": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[r:AFFECTS]->(g:Gender)
#             RETURN d.name AS disease, collect({gender: g.name, prevalence: r.prevalence}) AS gender_prevalence
#         """,
#         "prevalence": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[r:AFFECTS]->(n)
#             WHERE n:Gender OR n:AgeGroup
#             RETURN d.name AS disease, 
#                    collect(DISTINCT CASE WHEN n:Gender THEN {type: 'Gender', name: n.name, prevalence: r.prevalence} END) AS gender_prevalence,
#                    collect(DISTINCT CASE WHEN n:AgeGroup THEN {type: 'AgeGroup', name: n.name} END) AS age_groups
#         """,
#         "general": """
#             MATCH (d:Disease)
#             WHERE toLower(d.name) = toLower($entity)
#             OPTIONAL MATCH (d)-[r]-(n)
#             RETURN d.name AS disease, type(r) AS relationship, collect(n.name) AS related_entities
#         """
#     }
    
#     context = ""
#     with driver.session() as session:
#         try:
#             query = forward_query_templates.get(query_type, forward_query_templates["general"])
#             result = session.run(query, entity=entity)
#             record = result.single()
            
#             if not record:
#                 return ""
                
#             # Format results based on query type
#             if query_type == "symptoms":
#                 context += f"Disease: {record['disease']}\nSymptoms: {', '.join(record['symptoms'])}\n\n"
#             elif query_type == "treatments":
#                 context += f"Disease: {record['disease']}\nTreatments: {', '.join(record['treatments'])}\n\n"
#             elif query_type == "prevention":
#                 context += f"Disease: {record['disease']}\nPrevention Methods: {', '.join(record['prevention_methods'])}\n\n"
#             elif query_type == "risk_factors":
#                 context += f"Disease: {record['disease']}\nRisk Factors: {', '.join(record['risk_factors'])}\n\n"
#             elif query_type == "age_groups":
#                 context += f"Disease: {record['disease']}\nAge Groups: {', '.join(record['age_groups'])}\n\n"
#             elif query_type == "gender":
#                 gender_info = [f"{g['gender']} ({g['prevalence']}%)" for g in record['gender_prevalence'] if g and g['prevalence'] is not None]
#                 context += f"Disease: {record['disease']}\nGender Distribution: {', '.join(gender_info)}\n\n"
#             elif query_type == "prevalence":
#                 gender_info = [f"{g['name']} ({g['prevalence']}%)" for g in record['gender_prevalence'] if g and g['prevalence'] is not None]
#                 age_info = [g['name'] for g in record['age_groups'] if g]
#                 context += f"Disease: {record['disease']}\n"
#                 if gender_info:
#                     context += f"Gender Distribution: {', '.join(gender_info)}\n"
#                 if age_info:
#                     context += f"Age Groups: {', '.join(age_info)}\n"
#                 context += "\n"
#             else:
#                 context += f"Disease: {record['disease']}\n{record['relationship'].replace('_', ' ').title()}: {', '.join(record['related_entities'])}\n\n"
#         except Exception as e:
#             print(f"Error executing forward lookup for {entity}, {query_type}: {str(e)}")
            
#     return context


# def _execute_reverse_lookup(entity, query_type):
    # """
    # Execute a reverse lookup query (property → disease).
    
    # Args:
    #     entity (str): Entity name to look up
    #     query_type (str): Type of information being requested
        
    # Returns:
    #     str: Formatted context text or empty string if no results or unsupported query type
    # """
    # # Reverse lookup templates (property → disease)
    # reverse_query_templates = {
    #     "symptoms": """
    #         MATCH (s:Symptom)<-[:HAS_SYMPTOM]-(d:Disease)
    #         WHERE toLower(s.name) = toLower($entity)
    #         RETURN s.name AS symptom, collect(d.name) AS diseases
    #     """,
    #     "treatments": """
    #         MATCH (t:Treatment)<-[:HAS_TREATMENT]-(d:Disease)
    #         WHERE toLower(t.name) = toLower($entity)
    #         RETURN t.name AS treatment, collect(d.name) AS diseases
    #     """,
    #     "prevention": """
    #         MATCH (p:Prevention)<-[:HAS_PREVENTION]-(d:Disease)
    #         WHERE toLower(p.name) = toLower($entity)
    #         RETURN p.name AS prevention, collect(d.name) AS diseases
    #     """,
    #     "risk_factors": """
    #         MATCH (r:RiskFactor)<-[:HAS_RISK_FACTOR]-(d:Disease)
    #         WHERE toLower(r.name) = toLower($entity)
    #         RETURN r.name AS risk_factor, collect(d.name) AS diseases
    #     """,
    #     "age_groups": """
    #         MATCH (a:AgeGroup)<-[:AFFECTS]-(d:Disease)
    #         WHERE toLower(a.name) = toLower($entity)
    #         RETURN a.name AS age_group, collect(d.name) AS diseases
    #     """,
    #     "gender": """
    #         MATCH (g:Gender)<-[r:AFFECTS]-(d:Disease)
    #         WHERE toLower(g.name) = toLower($entity)
    #         RETURN g.name AS gender, collect({disease: d.name, prevalence: r.prevalence}) AS diseases
    #     """
    # }
    
    # # Return early if this query type doesn't support reverse lookup
    # if query_type not in reverse_query_templates:
    #     return ""
        
    # context = ""
    # with driver.session() as session:
    #     try:
    #         query = reverse_query_templates[query_type]
    #         result = session.run(query, entity=entity)
    #         record = result.single()
            
    #         if not record:
    #             return ""
                
    #         # Format results based on query type
    #         if query_type == "symptoms":
    #             context += f"Symptom: {record['symptom']}\nDiseases: {', '.join(record['diseases'])}\n\n"
    #         elif query_type == "treatments":
    #             context += f"Treatment: {record['treatment']}\nDiseases: {', '.join(record['diseases'])}\n\n"
    #         elif query_type == "prevention":
    #             context += f"Prevention: {record['prevention']}\nDiseases: {', '.join(record['diseases'])}\n\n"
    #         elif query_type == "risk_factors":
    #             context += f"Risk Factor: {record['risk_factor']}\nDiseases: {', '.join(record['diseases'])}\n\n"
    #         elif query_type == "age_groups":
    #             context += f"Age Group: {record['age_group']}\nDiseases: {', '.join(record['diseases'])}\n\n"
    #         elif query_type == "gender":
    #             disease_info = [f"{d['disease']} ({d['prevalence']}%)" for d in record['diseases'] if d['prevalence'] is not None]
    #             context += f"Gender: {record['gender']}\nDiseases: {', '.join(disease_info)}\n\n"
    #     except Exception as e:
    #         print(f"Error executing reverse lookup for {entity}, {query_type}: {str(e)}")
            
    # return context


def generate_response(question, use_graph=False):
    """Generate a response from the LLM, optionally using Neo4j for context."""
    # graph context is now handled by the calling function
    
    print(f'generate_response > question: {question}, use_graph: {use_graph}')
    
    response = ollama.generate(
        model="gemma3:4b",
        prompt=question
    )
    
    # Extract the response text
    if hasattr(response, "response"):
        return response.response
    elif hasattr(response, "text"):
        return response.text
    else:
        # Default fallback for any other format
        return str(response)


def evaluate_factual_accuracy(response):
    """Evaluate the factual accuracy of a response by checking entities against the Neo4j database."""
    entities = extract_entities(response)

    # Group entities by type
    entity_groups = {}
    for entity in entities:
        entity_type = entity['label']
        if entity_type not in entity_groups:
            entity_groups[entity_type] = []
        entity_groups[entity_type].append(entity['entity'])

    # Check relationships between entities
    verified_relationships = 0
    total_relationships = 0

    # Check disease-symptom relationships (both directions)
    if 'DISEASE' in entity_groups and 'SYMPTOM' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for symptom in entity_groups['SYMPTOM']:
                total_relationships += 1
                # Check both directions (disease→symptom and symptom→disease)
                if verify_entity_relationship(disease, symptom) or verify_entity_relationship(symptom, disease):
                    verified_relationships += 1

    # Check disease-treatment relationships (both directions)
    if 'DISEASE' in entity_groups and 'TREATMENT' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for treatment in entity_groups['TREATMENT']:
                total_relationships += 1
                if verify_entity_relationship(disease, treatment) or verify_entity_relationship(treatment, disease):
                    verified_relationships += 1

    # Check disease-prevention relationships (both directions)
    if 'DISEASE' in entity_groups and 'PREVENTION' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for prevention in entity_groups['PREVENTION']:
                total_relationships += 1
                if verify_entity_relationship(disease, prevention) or verify_entity_relationship(prevention, disease):
                    verified_relationships += 1

    # Check disease-risk factor relationships (both directions)
    if 'DISEASE' in entity_groups and 'RISK_FACTOR' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for risk_factor in entity_groups['RISK_FACTOR']:
                total_relationships += 1
                if verify_entity_relationship(disease, risk_factor) or verify_entity_relationship(risk_factor, disease):
                    verified_relationships += 1

    # Check disease-age group relationships (both directions)
    if 'DISEASE' in entity_groups and 'AGE_GROUP' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for age_group in entity_groups['AGE_GROUP']:
                total_relationships += 1
                if verify_entity_relationship(disease, age_group) or verify_entity_relationship(age_group, disease):
                    verified_relationships += 1

    # Check disease-gender relationships (both directions)
    if 'DISEASE' in entity_groups and 'GENDER' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for gender in entity_groups['GENDER']:
                total_relationships += 1
                if verify_entity_relationship(disease, gender) or verify_entity_relationship(gender, disease):
                    verified_relationships += 1
                    
    # Also check for list-based relationships (multiple entities of same type are related)
    if 'SYMPTOM' in entity_groups and len(entity_groups['SYMPTOM']) > 1:
        check_related_entities('SYMPTOM', entity_groups['SYMPTOM'], total_relationships, verified_relationships)
        
    if 'DISEASE' in entity_groups and len(entity_groups['DISEASE']) > 1:
        check_related_entities('DISEASE', entity_groups['DISEASE'], total_relationships, verified_relationships)

    # Calculate accuracy
    accuracy = verified_relationships / max(1, total_relationships)  # Avoid division by zero
    return accuracy
    
    
def check_related_entities(entity_type, entities, total_relationships, verified_relationships):
    """Check if multiple entities of the same type are related to each other through a common entity."""
    with driver.session() as session:
        for i in range(len(entities)):
            for j in range(i+1, len(entities)):
                # Check if both entities are related to the same disease/symptom
                if entity_type == 'SYMPTOM':
                    query = """
                    MATCH (s1:Symptom)<-[:HAS_SYMPTOM]-(d:Disease)-[:HAS_SYMPTOM]->(s2:Symptom)
                    WHERE toLower(s1.name) = toLower($entity1) AND toLower(s2.name) = toLower($entity2)
                    RETURN d.name as disease
                    """
                elif entity_type == 'DISEASE':
                    query = """
                    MATCH (d1:Disease)-[:HAS_SYMPTOM]->(s:Symptom)<-[:HAS_SYMPTOM]-(d2:Disease)
                    WHERE toLower(d1.name) = toLower($entity1) AND toLower(d2.name) = toLower($entity2)
                    RETURN s.name as common_symptom
                    """
                else:
                    continue
                    
                result = session.run(query, entity1=entities[i], entity2=entities[j])
                record = result.single()
                
                total_relationships += 1
                if record:
                    verified_relationships += 1


def evaluate_responses(questions):
    """
    Evaluate LLM responses with and without Neo4j integration for multiple questions.
    
    Args:
        questions (str or list): Question(s) to evaluate
        
    Returns:
        list or dict: Evaluation results for each question or single result if only one question provided
    """
    # Convert single question to list if needed
    if isinstance(questions, str):
        questions = [questions]
        single_question = True
    else:
        single_question = False

    results = []

    for idx, question in enumerate(questions, 1):
        print(f"Processing question {idx}/{len(questions)}: {question}")
        
        try:
            # Process the question and generate responses
            result = _process_single_question(question)
            results.append(result)
        except Exception as e:
            print(f"Error processing question: '{question}'. Error: {str(e)}")
            # Add a placeholder result with error information
            results.append({
                "question": question,
                "query_type": "error",
                "error": str(e),
                "prompt_without_graph": "",
                "prompt_with_graph": "",
                "response_without_graph": f"Error generating response: {str(e)}",
                "accuracy_without_graph": 0.0,
                "response_with_graph": f"Error generating response: {str(e)}",
                "accuracy_with_graph": 0.0
            })

    # Return single result if input was a single question
    return results[0] if single_question and results else results


def _process_single_question(question):
    """
    Process a single question, generating responses with and without Neo4j context.
    
    Args:
        question (str): The question to process
        
    Returns:
        dict: Evaluation results including prompts, responses and accuracy scores
    """
    # Define prompt templates for different query types
    prompt_templates = {
        "symptoms": "What are the typical symptoms that patients with {entities} experience? {instruction}",
        "treatments": "What treatments are commonly used for patients with {entities}? {instruction}",
        "prevention": "How can {entities} be prevented? {instruction}",
        "risk_factors": "What factors increase the risk of developing {entities}? {instruction}",
        "age_groups": "Which age groups are most commonly affected by {entities}? {instruction}",
        "gender": "How does {entities} affect different genders, including any differences in prevalence? {instruction}",
        "prevalence": "How common is {entities} across different populations, age groups, and genders? {instruction}",
        "general": "Can you provide detailed medical information about {entities}? {instruction}"
    }
    
    # Define reverse prompt templates for queries asking about properties->diseases
    reverse_prompt_templates = {
        "symptoms": "Which medical conditions or diseases commonly cause {entities}? {instruction}",
        "treatments": "Which medical conditions or diseases are typically treated with {entities}? {instruction}",
        "prevention": "Which diseases can be prevented through {entities}? {instruction}",
        "risk_factors": "Which diseases are associated with the risk factor {entities}? {instruction}",
        "age_groups": "Which diseases commonly affect patients in the {entities} age group? {instruction}",
        "gender": "Which diseases are more prevalent in {entities} patients? {instruction}"
    }

    # Define instructions based on graph context availability
    with_context_instruction = "Provide a structured, fact-oriented response using ONLY the provided context. Present information in a clear, concise format that explicitly states medical relationships. If the context doesn't contain the answer, clearly state this limitation."
    without_context_instruction = "Since no database information is available, simply state that you don't have knowledge about this specific question in your medical database. Be direct and brief."
    pretrained_instruction = "Provide a structured, fact-oriented response using established medical knowledge. Present information in a clear, concise format that explicitly states medical relationships."

    # Analyze question type
    entities, query_type = analyze_question(question)
    
    # Determine if this is a reverse lookup query (asking which diseases have a certain property)
    is_reverse_lookup = False
    reverse_lookup_keywords = [
        "which diseases", "what diseases", "list diseases", "find diseases", 
        "diseases that have", "diseases with", "diseases associated"
    ]
    
    for keyword in reverse_lookup_keywords:
        if keyword.lower() in question.lower():
            is_reverse_lookup = True
            break
    
    # Select appropriate prompt template
    if is_reverse_lookup and query_type in reverse_prompt_templates:
        prompt_template = reverse_prompt_templates[query_type]
    else:
        prompt_template = prompt_templates.get(query_type, prompt_templates["general"])
    
    entity_text = ", ".join(entities) if entities else "the specified condition"
    
    # Generate response without graph (using pre-trained knowledge)
    prompt_without_graph = _create_prompt(
        prompt_template, 
        entity_text, 
        question, 
        pretrained_instruction,
        False
    )
    
    response_without_graph = generate_response(prompt_without_graph, use_graph=False)
    
    # Generate response with graph
    context = execute_cypher_query(question)
    
    # Choose instruction based on context availability
    instruction = with_context_instruction if context else without_context_instruction
    
    prompt_with_graph = _create_prompt(
        prompt_template, 
        entity_text, 
        question, 
        instruction,
        True,
        context
    )
        
    response_with_graph = generate_response(prompt_with_graph, use_graph=True)

    # Evaluate factual accuracy
    accuracy_without_graph = evaluate_factual_accuracy(response_without_graph)
    accuracy_with_graph = evaluate_factual_accuracy(response_with_graph)

    # Return comprehensive results
    return {
        "question": question,
        "query_type": query_type,
        "is_reverse_lookup": is_reverse_lookup,
        "prompt_without_graph": prompt_without_graph,
        "prompt_with_graph": prompt_with_graph,
        "response_without_graph": response_without_graph,
        "accuracy_without_graph": accuracy_without_graph,
        "response_with_graph": response_with_graph,
        "accuracy_with_graph": accuracy_with_graph
    }


def _create_prompt(prompt_template, entity_text, question, instruction, use_graph, context=None):
    """
    Create a formatted prompt for the LLM based on template and parameters.
    
    Args:
        prompt_template (str): The template to use for creating the prompt
        entity_text (str): Text representing the entities in the question
        question (str): The original question
        instruction (str): Specific instructions for the model
        use_graph (bool): Whether this prompt is for a response using Neo4j
        context (str, optional): Neo4j context if available
        
    Returns:
        str: Formatted prompt for the LLM
    """
    # Format the base prompt with entities and instruction
    prompt = prompt_template.format(
        entities=entity_text,
        instruction=instruction
    )
    
    # Add the question
    prompt = f"{prompt}\n\nQuestion: {question}"
    
    # Common formatting instructions for both with and without Neo4j
    formatting_instructions = """
    
Provide a concise, structured response with clearly stated medical facts. Format your answer as follows:

1. Begin with a clear statement identifying the relationship between entities (e.g., "Influenza has the following symptoms:")
2. List each fact as a separate, brief statement (e.g., "- Fever", "- Cough", etc.)
3. Keep your response under 150 words
4. Include only verified medical information
5. Focus only on answering the specific question asked

Your response should be easy to parse for factual statements about medical relationships."""
    
    # For non-graph prompts
    if not use_graph:
        prompt += formatting_instructions
    # For graph prompts, add context if available
    elif use_graph:
        if context:
            prompt += f"\n\nContext:\n{context}\n\nBased ONLY on the above context information{formatting_instructions}"
        else:
            prompt += "\n\nNo database information available. You should respond by clearly stating that you don't have knowledge about this specific question in your medical database. Your response should be brief and direct, such as: 'I don't have information about this in my medical database.'"
    
    return prompt


def generate_report(evaluations, filename=None):
    """
    Generate a Markdown report from the evaluation results with comparison tables.
    
    Args:
        evaluations (list or dict): Evaluation results from evaluate_responses
        filename (str, optional): Output filename. If None, generates a timestamped filename
        
    Returns:
        str: Path to the generated report file
    """
    # Generate filename with current date and time if not provided
    if filename is None:
        current_time = datetime.now().strftime("%d-%m-%y_%H-%M")
        filename = f"report_{current_time}.md"
    
    # Ensure evaluations is a list even for single evaluations
    if not isinstance(evaluations, list):
        evaluations = [evaluations]
    
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Write report header
            _write_report_header(f, evaluations)
            
            # Write factual accuracy comparison
            accuracy_data = _calculate_accuracy_data(evaluations)
            _write_accuracy_comparison(f, evaluations, accuracy_data)
            
            # Write summary section
            _write_summary_section(f, accuracy_data)
            
            # Write comprehensive comparison table
            _write_comprehensive_comparison(f, evaluations)
            
            # Write Neo4j queries diagnostic table
            _write_neo4j_queries_diagnostics(f, evaluations)
                
        print(f"Report generated as {filename}")
        return filename
    except Exception as e:
        print(f"Error generating report: {str(e)}")
        return None


def _write_report_header(file, evaluations):
    """Write the report header section to the file."""
    file.write("# Medical Evaluation Report\n\n")
    file.write(f"Generated on: {datetime.now().strftime('%d-%m-%Y at %H:%M')}\n\n")
    file.write(f"Total questions evaluated: {len(evaluations)}\n\n")


def _calculate_accuracy_data(evaluations):
    """
    Calculate accuracy statistics from evaluations.
    
    Args:
        evaluations (list): List of evaluation results
        
    Returns:
        dict: Dictionary containing accuracy statistics
    """
    # Initialize totals
    total_without_db = 0
    total_with_db = 0
    question_count = len(evaluations)
    
    # Calculate totals
    for eval_item in evaluations:
        total_without_db += eval_item.get("accuracy_without_graph", 0)
        total_with_db += eval_item.get("accuracy_with_graph", 0)
    
    # Calculate averages
    avg_without_db = total_without_db / max(1, question_count)  # Avoid division by zero
    avg_with_db = total_with_db / max(1, question_count)        # Avoid division by zero
    improvement = avg_with_db - avg_without_db
    
    return {
        "total_without_db": total_without_db,
        "total_with_db": total_with_db,
        "question_count": question_count,
        "avg_without_db": avg_without_db,
        "avg_with_db": avg_with_db,
        "improvement": improvement
    }


def _write_accuracy_comparison(file, evaluations, accuracy_data):
    """Write the factual accuracy comparison table to the file."""
    file.write("## Factual Accuracy Comparison\n\n")
    file.write("| No. | Question | Without Neo4j | With Neo4j |\n")
    file.write("|-----|----------|---------------|------------|\n")
    
    for idx, eval_item in enumerate(evaluations, 1):
        accuracy_without = eval_item.get("accuracy_without_graph", 0)
        accuracy_with = eval_item.get("accuracy_with_graph", 0)
        
        # Format accuracies as percentages
        accuracy_without_str = f"{accuracy_without:.2%}"
        accuracy_with_str = f"{accuracy_with:.2%}"
        
        # Write table row
        file.write(f"| {idx} | {eval_item['question']} | {accuracy_without_str} | {accuracy_with_str} |\n")


def _write_summary_section(file, accuracy_data):
    """Write the summary section to the file."""
    file.write("\n## Summary\n\n")
    file.write(f"Total Questions: {accuracy_data['question_count']}\n\n")
    file.write(f"Average Factual Accuracy without Neo4j: {accuracy_data['avg_without_db']:.2%}\n\n")
    file.write(f"Average Factual Accuracy with Neo4j: {accuracy_data['avg_with_db']:.2%}\n\n")
    file.write(f"Overall Improvement: {accuracy_data['improvement']:.2%}\n\n")


def _write_comprehensive_comparison(file, evaluations):
    """Write the comprehensive comparison table to the file."""
    file.write("## Comprehensive Comparison\n\n")
    file.write("| No. | Original Question | Query Type | Without Neo4j |  With Neo4j |\n")
    file.write("|-----|-------------------|------------|---------------|-------------|\n")

    for idx, eval_item in enumerate(evaluations, 1):
        # Format the cells for the table
        without_neo4j_cell, with_neo4j_cell = _format_comparison_cells(eval_item)
        
        # Get the query type
        query_type = eval_item.get("query_type", "general")
        
        # Write formatted row to markdown table
        file.write(f"| {idx} | {eval_item['question']} | {query_type} | {without_neo4j_cell} | {with_neo4j_cell} |\n")


def _format_comparison_cells(eval_item):
    """
    Format the cells for the comprehensive comparison table.
    
    Args:
        eval_item (dict): Evaluation item containing prompt and response data
        
    Returns:
        tuple: Formatted cells for without Neo4j and with Neo4j
    """
    # Get responses
    response_without = _clean_response_text(eval_item.get("response_without_graph", ""))
    response_with = _clean_response_text(eval_item.get("response_with_graph", ""))
    
    # Format prompts for readability in markdown
    prompt_without = eval_item.get("prompt_without_graph", "").replace("\n", "<br>")
    prompt_with = eval_item.get("prompt_with_graph", "").replace("\n", "<br>")
    
    # Create combined cells with both prompt and response
    without_neo4j_cell = f"**Prompt:**<br>{prompt_without}<br><br>**Response:**<br>{response_without}"
    with_neo4j_cell = f"**Prompt:**<br>{prompt_with}<br><br>**Response:**<br>{response_with}"
    
    return without_neo4j_cell, with_neo4j_cell


def _write_neo4j_queries_diagnostics(file, evaluations):
    """Write a table containing Neo4j query diagnostics for each question."""
    file.write("\n## Neo4j Query Diagnostics\n\n")
    file.write("| No. | Question | Query Type | Reverse Lookup | Context Query | Context Result | Entity Extraction Results |\n")
    file.write("|-----|----------|------------|----------------|---------------|---------------|--------------------------|\n")
    
    # Reference the query templates defined in the application
    forward_query_templates = {
        "symptoms": "Disease → Symptoms",
        "treatments": "Disease → Treatments",
        "prevention": "Disease → Prevention Methods",
        "risk_factors": "Disease → Risk Factors",
        "age_groups": "Disease → Age Groups",
        "gender": "Disease → Gender Distribution",
        "prevalence": "Disease → Prevalence Distribution",
        "general": "Disease → General Information"
    }
    
    reverse_query_templates = {
        "symptoms": "Symptom → Diseases",
        "treatments": "Treatment → Diseases",
        "prevention": "Prevention Method → Diseases",
        "risk_factors": "Risk Factor → Diseases",
        "age_groups": "Age Group → Diseases",
        "gender": "Gender → Diseases"
    }
    
    for idx, eval_item in enumerate(evaluations, 1):
        question = eval_item['question']
        query_type = eval_item.get('query_type', 'general')
        is_reverse = eval_item.get('is_reverse_lookup', False)
        
        # Extract context from prompt with graph
        context = ""
        prompt_with_graph = eval_item.get('prompt_with_graph', '')
        if 'Context:' in prompt_with_graph:
            context_parts = prompt_with_graph.split('Context:')
            if len(context_parts) > 1:
                context_block = context_parts[1].split('Based ONLY')[0].strip()
                context = context_block.replace('\n', '<br>')
        
        # Extract entities from question
        entities, _ = analyze_question(question)
        entities_str = ', '.join(entities) if entities else 'None detected'
        
        # Format the reverse lookup status
        reverse_status = "Yes" if is_reverse else "No"
        
        # Determine query template used
        query_template = ""
        if is_reverse:
            if query_type in reverse_query_templates:
                query_template = reverse_query_templates[query_type]
            else:
                query_template = "No suitable reverse template"
        else:
            if query_type in forward_query_templates:
                query_template = forward_query_templates[query_type]
            else:
                query_template = "General query template"
        
        # Write row
        file.write(f"| {idx} | {question} | {query_type} | {reverse_status} | {query_template} | {context} | Entities: {entities_str} |\n")


def _clean_response_text(response_text):
    """
    Clean and format response text for display in the report.
    
    Args:
        response_text (str): Raw response text
        
    Returns:
        str: Cleaned response text
    """
    # Extract content between response=' and ' if present
    if "response='" in response_text:
        response_text = response_text.split("response='")[1].split("'")[0]
    
    # Clean responses for markdown
    return response_text.replace("\n", " ").replace("*", "").replace("---", "")


# def _execute_multi_entity_lookup(entities, node_type, relationship, display_name):
#     """
#     Execute a lookup for diseases that are related to all specified entities of a given type.
    
#     Args:
#         entities (list): List of entity names to look up
#         node_type (str): Type of nodes to look for (Symptom, Treatment, Prevention, etc.)
#         relationship (str): Relationship type to follow (HAS_SYMPTOM, HAS_TREATMENT, etc.)
#         display_name (str): Display name for the entity type in the output (symptoms, treatments, etc.)
        
#     Returns:
#         str: Formatted context text with diseases that relate to all the specified entities
#     """
#     if not entities or len(entities) == 0:
#         return ""
        
#     context = ""
#     with driver.session() as session:
#         try:
#             # For a single entity, use standard reverse lookup
#             if len(entities) == 1:
#                 # Map node type to query type
#                 node_to_query = {
#                     "Symptom": "symptoms",
#                     "Treatment": "treatments",
#                     "Prevention": "prevention",
#                     "RiskFactor": "risk_factors",
#                     "AgeGroup": "age_groups",
#                     "Gender": "gender"
#                 }
#                 query_type = node_to_query.get(node_type, "general")
#                 return _execute_reverse_lookup(entities[0], query_type)
            
#             # For multiple entities, find diseases that relate to ALL the entities
#             query = """
#             MATCH (d:Disease)
#             """
            
#             # Create MATCH conditions for each entity
#             for i, entity in enumerate(entities):
#                 query += f"""
#                 MATCH (d)-[:{relationship}]->(e{i}:{node_type})
#                 WHERE toLower(e{i}.name) = toLower($entity{i})
#                 """
            
#             # Complete the query to return matching diseases
#             query += """
#             RETURN d.name AS disease
#             """
            
#             # Create parameters dictionary
#             params = {}
#             for i, entity in enumerate(entities):
#                 params[f"entity{i}"] = entity
            
#             result = session.run(query, params)
#             records = result.values()
            
#             if not records:
#                 entity_list = ", ".join(entities)
#                 context += f"No diseases found that are related to all these {display_name}: {entity_list}\n\n"
#             else:
#                 diseases = [record[0] for record in records]
#                 entity_list = ", ".join(entities)
#                 context += f"{display_name.capitalize()}: {entity_list}\nDiseases: {', '.join(diseases)}\n\n"
                
#         except Exception as e:
#             print(f"Error executing multi-entity lookup for {entities}: {str(e)}")
            
#     return context


# def _execute_multi_symptom_lookup(symptoms):
#     """
#     Execute a lookup for diseases that have all specified symptoms.
    
#     Args:
#         symptoms (list): List of symptom names to look up
        
#     Returns:
#         str: Formatted context text with diseases that have all the specified symptoms
#     """
#     return _execute_multi_entity_lookup(symptoms, "Symptom", "HAS_SYMPTOM", "symptoms")


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
            model="gemma3:4b",
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
                
        print(f"Generated Cypher query for '{question}':\n{cypher_query}")
        
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
        print(f"Error generating Cypher query: {str(e)}")
        return None, {}


def execute_cypher_query(question):
    """
    Generate and execute a Cypher query from a natural language question.
    
    Args:
        question (str): Natural language question about medical information
        
    Returns:
        str: Formatted results from the Neo4j query
    """
    cypher_query, params = generate_cypher_query(question)
    
    if not cypher_query:
        return "Failed to generate Cypher query"
    
    try:
        with driver.session() as session:
            result = session.run(cypher_query, params)
            records = result.data()
            
            print(f"Query results: {records}")
            
            if not records:
                return "No results found."
            
            return records
            
    except Exception as e:
        error_message = str(e)
        print(f"Error executing Cypher query: {error_message}")
        return f"Error: {error_message}\nQuery: {cypher_query}"


# Example usage
sample_questions = [
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

# print(execute_cypher_query('What are the symptoms of Influenza?'))
evaluation = evaluate_responses(sample_questions)
generate_report(evaluation)
