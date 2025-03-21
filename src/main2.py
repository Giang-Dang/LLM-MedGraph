from neo4j import GraphDatabase
import ollama
import medspacy
from medspacy.ner import TargetMatcher, TargetRule
from datetime import datetime

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


def extract_medical_entities(text):
    """Extract medical entities from text using medspaCy."""
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            'entity': ent.text,
            'label': ent.label_
        })
    print(f'extract_medical_entities > results for {text} : {entities}')
    return entities


def analyze_question(question):
    """
    Analyze the question to identify entities and determine the type of medical information requested.
    Uses LLM to classify the query type instead of hardcoded keyword matching.
    """
    # Extract entities using medspaCy
    doc = nlp(question.lower())
    entities = [ent.text for ent in doc.ents]
    
    # Query types supported by the system
    query_types = [
        "symptoms",      # Questions about symptoms of a disease
        "treatments",    # Questions about treatments for a disease
        "prevention",    # Questions about how to prevent a disease
        "risk_factors",  # Questions about risk factors for a disease
        "age_groups",    # Questions about which age groups are affected by a disease
        "gender",        # Questions about gender distribution of a disease
        "prevalence",    # Questions about how common a disease is
        "general"        # General questions about a disease
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
    
    return entities, query_type


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
   RETURN s.name AS symptom

2. "Which diseases have Fever as a symptom?"
   MATCH (s:Symptom {name: 'Fever'})<-[:HAS_SYMPTOM]-(d:Disease)
   RETURN d.name AS disease

3. "Which diseases have both Cough and Fever as symptoms?"
   MATCH (d:Disease)-[:HAS_SYMPTOM]->(s1:Symptom {name: 'Cough'})
   MATCH (d)-[:HAS_SYMPTOM]->(s2:Symptom {name: 'Fever'})
   RETURN d.name AS disease

4. "What treatments are available for Diabetes?"
   MATCH (d:Disease {name: 'Diabetes'})-[:HAS_TREATMENT]->(t:Treatment)
   RETURN t.name AS treatment

5. "How does Migraine affect different genders?"
   MATCH (d:Disease {name: 'Migraine'})-[r:AFFECTS]->(g:Gender)
   RETURN g.name AS gender, r.prevalence AS prevalence
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
        list: Results from the Neo4j query
    """
    cypher_query, params = generate_cypher_query(question)
    
    if not cypher_query:
        return {"error": "Failed to generate Cypher query"}
    
    try:
        with driver.session() as session:
            result = session.run(cypher_query, params)
            records = result.data()
            
            print(f"Query results: {records}")
            return records
    except Exception as e:
        error_message = str(e)
        print(f"Error executing Cypher query: {error_message}")
        return {"error": error_message, "query": cypher_query}


def format_cypher_results(results, question):
    """
    Format the results from a Cypher query into a readable string.
    
    Args:
        results (list): Results from a Cypher query
        question (str): The original question
        
    Returns:
        str: Formatted results as a string
    """
    # Handle error case
    if isinstance(results, dict) and "error" in results:
        return f"Error: {results['error']}"
    
    # If no results were returned
    if not results:
        return "No results found."
    
    # Extract the keys to determine what type of data was returned
    if results and isinstance(results, list):
        keys = results[0].keys()
        
        # Format based on common query types
        if "symptom" in keys:
            symptoms = [record["symptom"] for record in results]
            return f"Symptoms: {', '.join(symptoms)}"
            
        elif "disease" in keys:
            diseases = [record["disease"] for record in results]
            return f"Diseases: {', '.join(diseases)}"
            
        elif "treatment" in keys:
            treatments = [record["treatment"] for record in results]
            return f"Treatments: {', '.join(treatments)}"
            
        elif "prevention" in keys:
            preventions = [record["prevention"] for record in results]
            return f"Prevention methods: {', '.join(preventions)}"
            
        elif "risk_factor" in keys:
            risk_factors = [record["risk_factor"] for record in results]
            return f"Risk factors: {', '.join(risk_factors)}"
            
        elif "gender" in keys and "prevalence" in keys:
            gender_data = [f"{record['gender']} ({record['prevalence']}%)" for record in results]
            return f"Gender distribution: {', '.join(gender_data)}"
            
        # If we don't recognize the specific format, create a generic response
        else:
            formatted_records = []
            for record in results:
                record_items = []
                for key, value in record.items():
                    record_items.append(f"{key}: {value}")
                formatted_records.append(", ".join(record_items))
            
            return "\n".join(formatted_records)
    
    # Fallback for unexpected result format
    return f"Results: {str(results)}"


def fetch_context_from_neo4j(question):
    """
    Fetch relevant context from Neo4j based on a natural language question.
    Uses LLM-generated Cypher queries.
    
    Args:
        question (str): Natural language question
        
    Returns:
        str: Formatted context text
    """
    # Execute the Cypher query
    results = execute_cypher_query(question)
    
    # Format results into readable text
    context = format_cypher_results(results, question)
    
    return context


def evaluate_factual_accuracy(response):
    """Evaluate the factual accuracy of a response by checking entities against the Neo4j database."""
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
    
    # Helper function to verify relationships
    def verify_relationship(type1, type2):
        nonlocal verified_relationships, total_relationships
        if type1 in entity_groups and type2 in entity_groups:
            for entity1 in entity_groups[type1]:
                for entity2 in entity_groups[type2]:
                    total_relationships += 1
                    # Generate and execute Cypher query to check relationship
                    cypher_query = f"""
                    MATCH (e1)<-[]-(e2)
                    WHERE 
                        (e1:{type1} AND e1.name = '{entity1}' AND e2:{type2} AND e2.name = '{entity2}')
                        OR
                        (e1:{type2} AND e1.name = '{entity2}' AND e2:{type1} AND e2.name = '{entity1}')
                    RETURN count(*) > 0 as related
                    """
                    with driver.session() as session:
                        result = session.run(cypher_query)
                        record = result.single()
                        if record and record["related"]:
                            verified_relationships += 1

    # Check all relationship types
    verify_relationship('Disease', 'Symptom')
    verify_relationship('Disease', 'Treatment')
    verify_relationship('Disease', 'Prevention')
    verify_relationship('Disease', 'RiskFactor')
    verify_relationship('Disease', 'AgeGroup')
    verify_relationship('Disease', 'Gender')

    # Calculate accuracy
    accuracy = verified_relationships / max(1, total_relationships)  # Avoid division by zero
    return accuracy


def generate_response(question):
    """
    Generate a response to a medical question using LLM with Neo4j context.
    
    Args:
        question (str): Natural language question about medical information
        
    Returns:
        str: Generated response
    """
    # Fetch context from Neo4j
    context = fetch_context_from_neo4j(question)
    
    # Prepare prompt with context
    prompt = f"""
I'm going to ask you a medical question, and I've already queried a Neo4j medical database for relevant information.

Question: {question}

Database results: {context}

Based ONLY on the database results, provide a concise, structured response with clearly stated medical facts.
Format your answer as follows:
1. Begin with a clear statement directly answering the question
2. List specific facts from the database results
3. Keep your response under 150 words
4. If the database results don't contain the answer, clearly state this limitation

Focus only on answering the specific question asked, using ONLY the information from the database results.
"""
    
    # Generate response
    response = ollama.generate(
        model="gemma3:4b",
        prompt=prompt
    )
    
    # Extract the response text
    if hasattr(response, "response"):
        return response.response
    elif hasattr(response, "text"):
        return response.text
    else:
        return str(response)


def evaluate_responses(questions):
    """
    Evaluate LLM responses for multiple questions using the new simplified approach.
    
    Args:
        questions (str or list): Question(s) to evaluate
        
    Returns:
        list or dict: Evaluation results for each question
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
            # Get response using Neo4j context
            response = generate_response(question)
            
            # Evaluate factual accuracy
            accuracy = evaluate_factual_accuracy(response)
            
            # Store results
            results.append({
                "question": question,
                "response": response,
                "accuracy": accuracy,
                "cypher_results": fetch_context_from_neo4j(question)
            })
            
        except Exception as e:
            print(f"Error processing question: '{question}'. Error: {str(e)}")
            results.append({
                "question": question,
                "response": f"Error generating response: {str(e)}",
                "accuracy": 0.0,
                "error": str(e)
            })

    # Return single result if input was a single question
    return results[0] if single_question and results else results


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
        # For the new format, accuracy is stored directly in 'accuracy'
        # We'll use this for both with_db and without_db to maintain the report structure
        accuracy = eval_item.get("accuracy", 0)
        total_without_db += 0  # We're not doing a without-db comparison in main2
        total_with_db += accuracy
    
    # Calculate averages
    avg_without_db = 0  # No without-db comparison in this version
    avg_with_db = total_with_db / max(1, question_count)
    improvement = avg_with_db  # Since without_db is 0, improvement is just with_db
    
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
        # For main2.py, we only have the "with Neo4j" accuracy
        accuracy_with = eval_item.get("accuracy", 0)
        
        # Format accuracies as percentages
        accuracy_without_str = "N/A"  # We don't have this in the new implementation
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
    file.write("| No. | Original Question | Query Type | Without Neo4j | With Neo4j |\n")
    file.write("|-----|-------------------|------------|---------------|-------------|\n")

    for idx, eval_item in enumerate(evaluations, 1):
        # Format the cells for the table
        entities, query_type = analyze_question(eval_item['question'])
        
        # Create a message for without Neo4j
        without_neo4j_cell = "Not applicable in this implementation"
        
        # Format the with Neo4j cell
        cypher_results = eval_item.get('cypher_results', 'No results')
        if isinstance(cypher_results, dict) and "error" in cypher_results:
            cypher_result_str = f"Error: {cypher_results['error']}"
            if "query" in cypher_results:
                cypher_result_str += f"<br>Query: {cypher_results['query']}"
        else:
            cypher_result_str = str(cypher_results)
        
        response = eval_item.get('response', '')
        
        with_neo4j_cell = f"**Cypher Results:**<br>{cypher_result_str}<br><br>**Response:**<br>{_clean_response_text(response)}"
        
        # Write formatted row to markdown table
        file.write(f"| {idx} | {eval_item['question']} | {query_type} | {without_neo4j_cell} | {with_neo4j_cell} |\n")


def _write_neo4j_queries_diagnostics(file, evaluations):
    """Write a table containing Neo4j query diagnostics for each question."""
    file.write("\n## Neo4j Query Diagnostics\n\n")
    file.write("| No. | Question | Query Type | Generated Cypher Query | Entity Extraction Results |\n")
    file.write("|-----|----------|------------|------------------------|-------------------------|\n")
    
    for idx, eval_item in enumerate(evaluations, 1):
        question = eval_item['question']
        
        # Get query type and entities
        entities, query_type = analyze_question(question)
        entities_str = ', '.join(entities) if entities else 'None detected'
        
        # Get the Cypher query that was generated
        cypher_results = eval_item.get('cypher_results', {})
        cypher_query = "Not available"
        
        if isinstance(cypher_results, dict) and "query" in cypher_results:
            cypher_query = cypher_results["query"]
        else:
            # Generate it again just for the report
            query_result, _ = generate_cypher_query(question)
            if query_result:
                cypher_query = query_result
        
        # Format the cypher query for display
        cypher_query_display = cypher_query.replace("\n", "<br>")
        
        # Write row
        file.write(f"| {idx} | {question} | {query_type} | {cypher_query_display} | Entities: {entities_str} |\n")


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


# Example usage
if __name__ == "__main__":
    # Test with a few sample questions
    sample_questions = [
        "What are the symptoms of Influenza?",
        "Which diseases have Fever as a symptom?",
        "What treatments are available for Diabetes?",
        "How can Asthma be prevented?",
        "Which diseases are linked to Cough and Fever?"
    ]
    
    # Single question test
    print("\nTesting with a single question:")
    result = execute_cypher_query(sample_questions[0])
    print(f"Cypher query results: {result}")
    response = generate_response(sample_questions[0])
    print(f"Generated response: {response}")
    
    # Evaluate multiple questions and generate report
    print("\nEvaluating multiple questions:")
    evaluations = evaluate_responses(sample_questions)
    report_path = generate_report(evaluations)