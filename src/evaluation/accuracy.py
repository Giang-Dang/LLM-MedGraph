"""
Accuracy evaluation module for assessing LLM responses.
"""
from ..db.connection import verify_entity_relationship 
from ..nlp.entity_extraction import extract_entities
from ..query.cypher import execute_cypher_query
from ..nlp.llm import generate_response
from ..config import get_logger

# Get module-specific logger
logger = get_logger("evaluation.accuracy")

def evaluate_factual_accuracy(response):
    """
    Evaluate the factual accuracy of a response by checking entities against the Neo4j database.
    
    Args:
        response (str): The response to evaluate
        
    Returns:
        float: Accuracy score between 0 and 1
    """
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
    """
    Check if multiple entities of the same type are related to each other through a common entity.
    
    Args:
        entity_type (str): Type of entities to check
        entities (list): List of entity names
        total_relationships (int): Counter for total relationships checked
        verified_relationships (int): Counter for verified relationships
        
    Returns:
        tuple: Updated (total_relationships, verified_relationships) counts
    """
    from ..db.connection import run_query
    
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
                
            params = {"entity1": entities[i], "entity2": entities[j]}
            result = run_query(query, params)
            
            total_relationships += 1
            if result:
                verified_relationships += 1
                
    return total_relationships, verified_relationships


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
    
    logger.info(f"Evaluating responses for {len(questions)} questions")

    for idx, question in enumerate(questions, 1):
        logger.info(f"Processing question {idx}/{len(questions)}: {question}")
        
        try:
            # Process the question and generate responses
            result = _process_single_question(question)
            results.append(result)
        except Exception as e:
            logger.error(f"Error processing question: '{question}'. Error: {str(e)}", exc_info=True)
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
    from ..nlp.entity_extraction import analyze_question
    
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
        
    response_with_graph = generate_response(prompt_with_graph, use_graph=True, context=context)

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