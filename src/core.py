from db import run_query
from nlp import analyze_question
from openie_wrapper import extract_triplets
from ollama_wrapper import generate_response


def verify_triplet(triplet):
    """Verify a triplet against Neo4j."""
    subject, predicate, obj = triplet['subject'], triplet['relation'], triplet['object']
    query = (
        "MATCH (s)-[r]->(o) "
        "WHERE s.name = $subject AND type(r) = $predicate AND o.name = $object "
        "RETURN s, r, o"
    )
    result = run_query(query,
                       subject=subject,
                       predicate=predicate.upper().replace(" ", "_"),
                       object=obj)
    return result.single() is not None


def fetch_context_from_neo4j(entities, query_type):
    """Fetch context from Neo4j by query type."""
    query_templates = {
        "symptoms": """
            MATCH (d:Disease {name: $entity})-[:HAS_SYMPTOM]->(s:Symptom)
            RETURN d.name AS disease, collect(s.name) AS symptoms
        """,
        "treatments": """
            MATCH (d:Disease {name: $entity})-[:HAS_TREATMENT]->(t:Treatment)
            RETURN d.name AS disease, collect(t.name) AS treatments
        """,
        "causes": """
            MATCH (d:Disease {name: $entity})-[:HAS_CAUSE]->(c:Cause)
            RETURN d.name AS disease, collect(c.name) AS causes
        """,
        "prevention": """
            MATCH (d:Disease {name: $entity})-[:HAS_PREVENTION]->(p:Prevention)
            RETURN d.name AS disease, collect(p.name) AS prevention_methods
        """,
        "general": """
            MATCH (d:Disease {name: $entity})-[r]-(n)
            RETURN d.name AS disease, type(r) AS relationship, collect(n.name) AS related_entities
        """
    }

    context = ""
    for entity in entities:
        query = query_templates.get(query_type, query_templates["general"])
        result = run_query(query, entity=entity)
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


def generate_application_response(question, use_graph=False):
    """Generate a response from the LLM, optionally using Neo4j for context."""
    if use_graph:
        entities, query_type = analyze_question(question)
        context = fetch_context_from_neo4j(entities, query_type)
        if context:
            question = f"{question}\n\nContext:\n{context}"

    response = ollama.generate(
        model="deepseek-r1:14b",
        prompt=question
    )
    # Ensure we return a string rather than a response object
    if hasattr(response, "text"):
        return response.text
    else:
        return str(response)


def evaluate_responses(question):
    """Generate and evaluate responses with and without graph context."""
    prompt = (
        "You are a medical expert. Please provide detailed and accurate answers to the following medical question. "
        "If you are uncertain or lack sufficient information to answer, acknowledge this explicitly and refrain from providing an answer.\n\n"
        f"Question: {question}"
    )

    response_without_graph = generate_application_response(
        prompt, use_graph=False)
    response_with_graph = generate_application_response(prompt, use_graph=True)

    triplets_without_graph = extract_triplets(response_without_graph)
    triplets_with_graph = extract_triplets(response_with_graph)

    accuracy_without_graph = sum(verify_triplet(
        t) for t in triplets_without_graph) / len(triplets_without_graph)
    accuracy_with_graph = sum(verify_triplet(t)
                              for t in triplets_with_graph) / len(triplets_with_graph)

    return {
        "response_without_graph": response_without_graph,
        "accuracy_without_graph": accuracy_without_graph,
        "response_with_graph": response_with_graph,
        "accuracy_with_graph": accuracy_with_graph
    }
