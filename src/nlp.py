import spacy
from config import SPACY_MODEL

nlp = spacy.load(SPACY_MODEL)


def analyze_question(question):
    """Analyze the question to extract entities and determine query type."""
    doc = nlp(question.lower())
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
