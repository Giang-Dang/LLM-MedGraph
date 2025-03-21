from neo4j import GraphDatabase
import ollama
import medspacy
from medspacy.ner import TargetMatcher, TargetRule

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
    TargetRule("Diabetes Mellitus", "DISEASE"),
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
    TargetRule("Influenza Vaccination", "PREVENTION"),
    TargetRule("Healthy Diet and Weight Management", "PREVENTION"),
    TargetRule("Blood Pressure Monitoring and Low-Sodium Diet", "PREVENTION"),
    TargetRule("Avoid Allergens and Air Pollutants", "PREVENTION"),
    TargetRule("Regular Sleep and Stress Management", "PREVENTION")
]

# Define treatments
treatment_rules = [
    TargetRule("Antiviral Medications", "TREATMENT"),
    TargetRule("Oseltamivir", "TREATMENT"),
    TargetRule("Zanamivir", "TREATMENT"),
    TargetRule("Insulin Therapy", "TREATMENT"),
    TargetRule("Oral Hypoglycemics", "TREATMENT"),
    TargetRule("Antihypertensive Medications", "TREATMENT"),
    TargetRule("ACE Inhibitors", "TREATMENT"),
    TargetRule("Beta-Blockers", "TREATMENT"),
    TargetRule("Bronchodilators", "TREATMENT"),
    TargetRule("Inhaled Corticosteroids", "TREATMENT"),
    TargetRule("Analgesics", "TREATMENT"),
    TargetRule("NSAIDs", "TREATMENT"),
    TargetRule("Triptans", "TREATMENT")
]

# Combine all rules
all_rules = disease_rules + symptom_rules + prevention_rules + treatment_rules

# Add rules to the matcher
target_matcher.add(all_rules)


def extract_medical_entities(text):
    """Extract medical entities from text using medspaCy."""
    print(f'extract_medical_entities {text}')
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            'entity': ent.text,
            'label': ent.label_
        })
    return entities


def verify_entity_relationship(entity1, entity2):
    """Verify if there's a relationship between two entities in the Neo4j database."""
    print(f'verify_entity_relationship {entity1}, {entity2}')
    with driver.session() as session:
        result = session.run(
            "MATCH (s)-[r]->(o) "
            "WHERE s.name = $entity1 AND o.name = $entity2 "
            "RETURN s, r, o",
            entity1=entity1,
            entity2=entity2
        )
        return result.single() is not None


def analyze_question(question):
    """Analyze the question to identify entities and determine the type of medical information requested."""
    print(f'analyze_question {question}')
    doc = nlp(question.lower())
    print('doc', doc)
    entities = [ent.text for ent in doc.ents]

    keywords_to_query_type = {
        "symptom": "symptoms",
        "treatment": "treatments",
        "treat": "treatments",
        "cause": "causes",
        "etiology": "causes",
        "prevention": "prevention",
        "prevent": "prevention"
    }

    query_type = "general"
    for keyword, q_type in keywords_to_query_type.items():
        if keyword in question:
            query_type = q_type
            break

    return entities, query_type


def fetch_context_from_neo4j(entities, query_type):
    """Fetch relevant context from Neo4j based on entities and query type."""
    print(f'fetch_context_from_neo4j {entities}, {query_type}')
    query_templates = {
        "symptoms": """
            MATCH (d:Disease)
            WHERE toLower(d.name) = toLower($entity)
            OPTIONAL MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
            RETURN d.name AS disease, collect(s.name) AS symptoms
        """,
        "treatments": """
            MATCH (d:Disease)
            WHERE toLower(d.name) = toLower($entity)
            OPTIONAL MATCH (d)-[:HAS_TREATMENT]->(t:Treatment)
            RETURN d.name AS disease, collect(t.name) AS treatments
        """,
        "causes": """
            MATCH (d:Disease)
            WHERE toLower(d.name) = toLower($entity)
            OPTIONAL MATCH (d)-[:HAS_CAUSE]->(c:Cause)
            RETURN d.name AS disease, collect(c.name) AS causes
        """,
        "prevention": """
            MATCH (d:Disease)
            WHERE toLower(d.name) = toLower($entity)
            OPTIONAL MATCH (d)-[:HAS_PREVENTION]->(p:Prevention)
            RETURN d.name AS disease, collect(p.name) AS prevention_methods
        """,
        "general": """
            MATCH (d:Disease)
            WHERE toLower(d.name) = toLower($entity)
            OPTIONAL MATCH (d)-[r]-(n)
            RETURN d.name AS disease, type(r) AS relationship, collect(n.name) AS related_entities
        """
    }

    print(f'query_templates {query_templates}')

    context = ""
    with driver.session() as session:
        for entity in entities:
            query = query_templates.get(query_type, query_templates["general"])
            result = session.run(query, entity=entity)
            print(entity, 'result', result)
            for record in result:
                if query_type == "symptoms":
                    context += f"Disease: {record['disease']}\nSymptoms: {', '.join(record['symptoms'])}\n\n"
                elif query_type == "treatments":
                    context += f"Disease: {record['disease']}\nTreatments: {', '.join(record['treatments'])}\n\n"
                elif query_type == "causes":
                    context += f"Disease: {record['disease']}\nCauses: {', '.join(record['causes'])}\n\n"
                elif query_type == "prevention":
                    context += f"Disease: {record['disease']}\nPrevention Methods: {', '.join(record['prevention_methods'])}\n\n"
                else:
                    context += f"Disease: {record['disease']}\n{record['relationship'].replace('_', ' ').title()}: {', '.join(record['related_entities'])}\n\n"
    return context


def get_role_instructions(role_name="general"):
    """Fetch role-specific instructions from the Neo4j database."""
    print(f'get_role_instructions for {role_name}')
    
    with driver.session() as session:
        # Query for role information, instructions, and response style
        result = session.run("""
            MATCH (r:Role {name: $role_name})
            OPTIONAL MATCH (r)-[:HAS_INSTRUCTION]->(i:Instruction)
            RETURN r.responseStyle AS responseStyle, 
                   r.description AS roleDescription,
                   i.details AS instructionDetails
        """, role_name=role_name)
        
        record = result.single()
        if record:
            return {
                "responseStyle": record["responseStyle"],
                "roleDescription": record["roleDescription"],
                "instructionDetails": record["instructionDetails"]
            }
        else:
            # Fallback to general role if specified role not found
            result = session.run("""
                MATCH (r:Role {name: 'general'})
                OPTIONAL MATCH (r)-[:HAS_INSTRUCTION]->(i:Instruction)
                RETURN r.responseStyle AS responseStyle, 
                       r.description AS roleDescription,
                       i.details AS instructionDetails
            """)
            record = result.single()
            if record:
                return {
                    "responseStyle": record["responseStyle"],
                    "roleDescription": record["roleDescription"],
                    "instructionDetails": record["instructionDetails"]
                }
            else:
                # Default values if no roles found
                return {
                    "responseStyle": "balanced",
                    "roleDescription": "Provide a balanced response with direct answer and context",
                    "instructionDetails": "Provide a balanced response that combines a direct answer with some contextual explanation."
                }


def get_query_template(role_name="general"):
    """Fetch the query template for a specific role."""
    print(f'get_query_template for {role_name}')
    
    with driver.session() as session:
        # Query for the template associated with the role
        result = session.run("""
            MATCH (r:Role {name: $role_name})
            OPTIONAL MATCH (qt:QueryTemplate)
            WHERE qt.name CONTAINS r.name
            RETURN qt.template AS template
        """, role_name=role_name)
        
        record = result.single()
        if record and record["template"]:
            return record["template"]
        else:
            # Fallback to general template
            result = session.run("""
                MATCH (qt:QueryTemplate {name: 'Teacher Query'})
                RETURN qt.template AS template
            """)
            record = result.single()
            if record and record["template"]:
                return record["template"]
            else:
                # Default template if none found
                return "Provide a clear and informative response to the question."


def format_prompt_for_role(question, role_name, medical_context=""):
    """Format the prompt based on the role's instructions and query template."""
    role_info = get_role_instructions(role_name)
    query_template = get_query_template(role_name)
    
    # Build a prompt that incorporates the role's style and instructions
    prompt = f"""
As a medical AI assistant, please respond to the following question in the {role_info['responseStyle']} style.

Role Description: {role_info['roleDescription']}
Instructions: {role_info['instructionDetails']}
Response Format: {query_template}

Question: {question}
"""

    # Add medical context if available
    if medical_context:
        prompt += f"\n\nMedical Context:\n{medical_context}"
        
    return prompt


def generate_response(question, role_name="general", use_graph=False):
    """Generate a response from the LLM, optionally using Neo4j for context and role-specific formatting."""
    print(f'generate_response for question: {question}, role: {role_name}, use_graph: {use_graph}')
    
    medical_context = ""
    if use_graph:
        entities, query_type = analyze_question(question)
        medical_context = fetch_context_from_neo4j(entities, query_type)
    
    # Format the prompt based on role and context
    prompt = format_prompt_for_role(question, role_name, medical_context)
    
    print(f'Formatted prompt: {prompt}')
    
    # Generate response using Ollama
    response = ollama.generate(
        model="gemma3:4b",
        prompt=prompt
    )
    
    # Ensure we return a string rather than a response object
    if hasattr(response, "response"):
        return response.response
    elif isinstance(response, dict) and "response" in response:
        return response["response"]
    elif hasattr(response, "text"):
        return response.text
    else:
        return str(response)


def evaluate_factual_accuracy(response):
    """Evaluate the factual accuracy of a response by checking entities against the Neo4j database."""
    print(f'evaluate_factual_accuracy {response}')
    entities = extract_medical_entities(response)
    
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
    
    # Check disease-symptom relationships
    if 'DISEASE' in entity_groups and 'SYMPTOM' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for symptom in entity_groups['SYMPTOM']:
                total_relationships += 1
                if verify_entity_relationship(disease, symptom):
                    verified_relationships += 1
    
    # Check disease-treatment relationships
    if 'DISEASE' in entity_groups and 'TREATMENT' in entity_groups:
        for disease in entity_groups['DISEASE']:
            for treatment in entity_groups['TREATMENT']:
                total_relationships += 1
                if verify_entity_relationship(disease, treatment):
                    verified_relationships += 1
    
    # Calculate accuracy
    accuracy = verified_relationships / max(1, total_relationships)  # Avoid division by zero
    return accuracy


def evaluate_responses_by_role(question, roles=None):
    """Evaluate LLM responses with different roles, with and without Neo4j integration."""
    if roles is None:
        roles = ["student", "teacher", "parents", "researcher", "calculator", "general"]
    
    print(f'evaluate_responses_by_role for question: {question}, roles: {roles}')
    
    results = {}
    
    for role in roles:
        print(f'Evaluating for role: {role}')
        
        # Generate responses with and without graph context
        response_without_graph = generate_response(question, role, use_graph=False)
        response_with_graph = generate_response(question, role, use_graph=True)
        
        # Evaluate factual accuracy
        accuracy_without_graph = evaluate_factual_accuracy(response_without_graph)
        accuracy_with_graph = evaluate_factual_accuracy(response_with_graph)
        
        results[role] = {
            "response_without_graph": response_without_graph,
            "accuracy_without_graph": accuracy_without_graph,
            "response_with_graph": response_with_graph,
            "accuracy_with_graph": accuracy_with_graph
        }
    
    return results


def generate_role_based_report(evaluation_results, filename="role_based_report.md"):
    """Generate a Markdown report comparing responses across different roles."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Role-Based Medical Response Evaluation\n\n")
        
        # Overall summary
        f.write("## Summary\n\n")
        f.write("This report compares responses to a medical question across different user roles, both with and without Neo4j knowledge graph integration.\n\n")
        
        # Add a table summarizing accuracy by role
        f.write("### Accuracy by Role\n\n")
        f.write("| Role | Without Neo4j | With Neo4j | Improvement |\n")
        f.write("|------|--------------|------------|-------------|\n")
        
        for role, data in evaluation_results.items():
            accuracy_without = data["accuracy_without_graph"]
            accuracy_with = data["accuracy_with_graph"]
            improvement = accuracy_with - accuracy_without
            
            f.write(f"| {role.capitalize()} | {accuracy_without:.2%} | {accuracy_with:.2%} | {improvement:.2%} |\n")
        
        f.write("\n")
        
        # Detailed results by role
        f.write("## Detailed Results by Role\n\n")
        
        for role, data in evaluation_results.items():
            f.write(f"### {role.capitalize()} Role\n\n")
            
            # Role instructions from Neo4j
            role_info = get_role_instructions(role)
            f.write("#### Role Information\n\n")
            f.write(f"- **Response Style:** {role_info['responseStyle']}\n")
            f.write(f"- **Role Description:** {role_info['roleDescription']}\n")
            f.write(f"- **Instruction Details:** {role_info['instructionDetails']}\n\n")
            
            # Response without Neo4j
            f.write("#### Response Without Neo4j\n\n")
            f.write(f"{data['response_without_graph']}\n\n")
            f.write(f"**Factual Accuracy:** {data['accuracy_without_graph']:.2%}\n\n")
            
            # Response with Neo4j
            f.write("#### Response With Neo4j\n\n")
            f.write(f"{data['response_with_graph']}\n\n")
            f.write(f"**Factual Accuracy:** {data['accuracy_with_graph']:.2%}\n\n")
            
            # Comparison
            f.write("#### Analysis\n\n")
            improvement = data['accuracy_with_graph'] - data['accuracy_without_graph']
            f.write(f"- **Accuracy Improvement:** {improvement:.2%}\n")
            f.write("- **Observations:** ")
            
            if improvement > 0.2:
                f.write("Significant improvement in factual accuracy with Neo4j integration.\n\n")
            elif improvement > 0:
                f.write("Moderate improvement in factual accuracy with Neo4j integration.\n\n")
            elif improvement == 0:
                f.write("No change in factual accuracy with Neo4j integration.\n\n")
            else:
                f.write("Decrease in factual accuracy with Neo4j integration - requires investigation.\n\n")
        
        # Overall conclusions
        f.write("## Conclusions\n\n")
        
        # Calculate average improvement
        total_improvement = sum(data['accuracy_with_graph'] - data['accuracy_without_graph'] 
                               for data in evaluation_results.values())
        avg_improvement = total_improvement / len(evaluation_results)
        
        f.write(f"- **Average Accuracy Improvement:** {avg_improvement:.2%}\n")
        
        # Find best role for accuracy
        best_role_with_graph = max(evaluation_results.items(), 
                                  key=lambda x: x[1]['accuracy_with_graph'])
        
        f.write(f"- **Best Role for Accuracy:** {best_role_with_graph[0].capitalize()} " +
                f"({best_role_with_graph[1]['accuracy_with_graph']:.2%})\n")
        
        # General conclusion
        if avg_improvement > 0:
            f.write("- **General Finding:** Neo4j knowledge graph integration improves response accuracy across roles.\n")
        else:
            f.write("- **General Finding:** Neo4j knowledge graph integration did not consistently improve accuracy.\n")


# Example usage
def main():
    """Run the evaluation with a sample question across different roles."""
    question = "What are the primary symptoms of Influenza?"
    
    # Define roles to test
    roles = ["student", "teacher", "parents", "researcher", "calculator", "general"]
    
    # Evaluate responses for each role
    results = evaluate_responses_by_role(question, roles)
    
    # Generate the report
    generate_role_based_report(results)
    print(f"Role-based report generated as role_based_report.md")


if __name__ == "__main__":
    main()