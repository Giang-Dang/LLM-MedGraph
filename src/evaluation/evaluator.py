"""
Medical knowledge graph evaluator module.
"""
import json
import ollama
from datetime import datetime
from difflib import SequenceMatcher
# Change relative imports to absolute imports
from src.config import LLM_MODEL, get_logger
from src.nlp.entity_extraction import analyze_question
from src.query.query_generator import generate_cypher_query, execute_query

# Get module-specific logger
logger = get_logger("evaluation.evaluator")

def evaluate_question_answer_pairs(qa_pairs, report_filename):
    """
    Evaluate the system on a list of question-answer pairs.
    
    Args:
        qa_pairs (list): List of dictionaries containing questions and expected answers
        report_filename (str): Filename for the evaluation report
        
    Returns:
        dict: Evaluation metrics and individual test results
    """
    logger.info(f"Starting evaluation on {len(qa_pairs)} question-answer pairs")
    results = []
    total_score = 0
    
    for idx, qa_pair in enumerate(qa_pairs):
        question = qa_pair["question"]
        expected_answer = qa_pair["expected_answer"] if "expected_answer" in qa_pair else None
        
        # Process the question
        logger.info(f"Processing question {idx+1}/{len(qa_pairs)}: {question}")
        entities, query_type = analyze_question(question)
        
        # Generate and execute query
        query = generate_cypher_query(entities, query_type)
        query_results = execute_query(query)
        
        # Check if query execution returned an error
        if query_results and "error" in query_results[0]:
            system_answer = f"Error: {query_results[0]['error']}"
            score = 0
            explanation = "Query execution failed"
            logger.warning(f"Query execution failed: {query_results[0]['error']}")
        else:
            # Format the answer based on query results
            system_answer = format_answer(question, entities, query_type, query_results)
            
            # If expected answer is provided, evaluate the system answer
            if expected_answer:
                score, explanation = evaluate_answer(system_answer, expected_answer)
                logger.debug(f"Answer evaluation score: {score}, explanation: {explanation}")
            else:
                score = None
                explanation = "No expected answer provided"
                logger.debug("No expected answer provided for evaluation")
        
        # Store the result
        result = {
            "question": question,
            "entities": entities,
            "query_type": query_type,
            "query": query,
            "query_results": query_results,
            "system_answer": system_answer,
            "expected_answer": expected_answer,
            "score": score,
            "explanation": explanation
        }
        
        results.append(result)
        
        if score is not None:
            total_score += score
    
    # Calculate overall metrics
    num_evaluated = sum(1 for r in results if r["score"] is not None)
    average_score = total_score / num_evaluated if num_evaluated > 0 else 0
    
    logger.info(f"Evaluation complete. Average score: {average_score:.2f}, Total score: {total_score:.2f}")
    
    # Generate the report
    evaluation_report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "num_questions": len(qa_pairs),
            "num_evaluated": num_evaluated,
            "average_score": average_score,
            "total_score": total_score
        },
        "results": results
    }
    
    # Save the report
    if report_filename:
        save_evaluation_report(evaluation_report, report_filename)
    
    return evaluation_report

def format_answer(question, entities, query_type, query_results):
    """
    Format the answer based on query results.
    
    Args:
        question (str): The original question
        entities (list): Extracted entities
        query_type (str): Type of query
        query_results (list): Results from Neo4j query
        
    Returns:
        str: Formatted answer
    """
    logger.debug(f"Formatting answer for question: {question}")
    
    # If no results were found
    if not query_results or len(query_results) == 0:
        logger.debug("No results found for question")
        return "I couldn't find any information for your question."
    
    # Use LLM to generate a natural language answer
    prompt = f"""
    Question: {question}
    
    Query Type: {query_type}
    Entities: {', '.join(entities) if entities else 'None'}
    
    Database Results: 
    {json.dumps(query_results, indent=2)}
    
    Format a clear, concise answer based on these results. 
    If multiple diseases or concepts are returned, mention each with its relevant information.
    Make the answer conversational but informative. 
    If no relevant information was found, say so clearly.
    
    Answer:
    """
    
    try:
        # Call the LLM to format the answer
        logger.debug("Using LLM to format answer")
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt
        )
        
        # Extract the response
        if hasattr(response, "response"):
            formatted_answer = response.response.strip()
        elif hasattr(response, "text"):
            formatted_answer = response.text.strip()
        else:
            formatted_answer = str(response).strip()
        
        logger.debug(f"LLM formatted answer (first 100 chars): {formatted_answer[:100]}...")
        return formatted_answer
        
    except Exception as e:
        logger.error(f"Error formatting answer with LLM: {str(e)}")
        
        # Fall back to simple formatting
        logger.debug("Falling back to template-based answer formatting")
        formatted_answer = "Based on the medical database:\n\n"
        
        for result in query_results:
            if "disease" in result:
                disease = result["disease"]
                formatted_answer += f"For {disease}:\n"
                
                # Add symptoms if available
                if "symptoms" in result and result["symptoms"]:
                    symptoms = result["symptoms"]
                    if symptoms:
                        formatted_answer += f"- Symptoms: {', '.join(symptoms)}\n"
                
                # Add treatments if available
                if "treatments" in result and result["treatments"]:
                    treatments = result["treatments"]
                    if treatments:
                        formatted_answer += f"- Treatments: {', '.join(treatments)}\n"
                
                # Add preventions if available
                if "preventions" in result and result["preventions"]:
                    preventions = result["preventions"]
                    if preventions:
                        formatted_answer += f"- Preventions: {', '.join(preventions)}\n"
                
                # Add risk factors if available
                if "risk_factors" in result and result["risk_factors"]:
                    risk_factors = result["risk_factors"]
                    if risk_factors:
                        formatted_answer += f"- Risk Factors: {', '.join(risk_factors)}\n"
                
                formatted_answer += "\n"
        
        return formatted_answer

def evaluate_answer(system_answer, expected_answer):
    """
    Evaluate the system's answer against the expected answer.
    
    Args:
        system_answer (str): The answer generated by the system
        expected_answer (str): The expected correct answer
        
    Returns:
        tuple: (score, explanation) where score is a float between 0 and 1
    """
    logger.debug("Evaluating system answer against expected answer")
    
    # Use LLM to evaluate the answer
    prompt = f"""
    You are evaluating a medical question answering system.
    
    System Answer: {system_answer}
    Expected Answer: {expected_answer}
    
    Score the system answer on a scale of 0.0 to 1.0 based on:
    1. Correctness - Does it provide factually correct information?
    2. Completeness - Does it cover all important aspects in the expected answer?
    3. Relevance - Does it directly address the question?
    
    First, provide a score between 0.0 and 1.0, then write a brief explanation for your scoring.
    Format your response exactly like this:
    SCORE: [number between 0 and 1]
    EXPLANATION: [your explanation]
    """
    
    try:
        # Call the LLM to evaluate the answer
        logger.debug("Using LLM to evaluate answer")
        response = ollama.generate(
            model=LLM_MODEL,
            prompt=prompt
        )
        
        # Extract the response
        if hasattr(response, "response"):
            evaluation = response.response.strip()
        elif hasattr(response, "text"):
            evaluation = response.text.strip()
        else:
            evaluation = str(response).strip()
        
        # Parse the evaluation to extract score and explanation
        score_line = [line for line in evaluation.split("\n") if line.strip().startswith("SCORE:")][0]
        score = float(score_line.replace("SCORE:", "").strip())
        
        explanation_line = [line for line in evaluation.split("\n") if line.strip().startswith("EXPLANATION:")][0]
        explanation = explanation_line.replace("EXPLANATION:", "").strip()
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        logger.info(f"LLM evaluation score: {score:.2f}")
        logger.debug(f"LLM evaluation explanation: {explanation}")
        
        return score, explanation
        
    except Exception as e:
        logger.error(f"Error evaluating answer with LLM: {str(e)}")
        
        # Fall back to simple string similarity
        logger.debug("Falling back to string similarity for answer evaluation")
        similarity = SequenceMatcher(None, system_answer.lower(), expected_answer.lower()).ratio()
        
        explanation = f"Fallback similarity score: {similarity:.2f}"
        logger.info(f"Fallback similarity score: {similarity:.2f}")
        
        return similarity, explanation

def save_evaluation_report(evaluation_report, report_filename):
    """
    Save the evaluation report to a file.
    
    Args:
        evaluation_report (dict): The evaluation report data
        report_filename (str): Filename for the report
    """
    logger.info(f"Saving evaluation report to {report_filename}")
    
    try:
        # Check if it's a markdown file
        if report_filename.endswith('.md'):
            # Generate markdown report
            md_content = generate_markdown_report(evaluation_report)
            
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(md_content)
                
        # Otherwise save as JSON
        else:
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(evaluation_report, f, indent=2, ensure_ascii=False)
                
        logger.info(f"Evaluation report saved successfully to {report_filename}")
        
    except Exception as e:
        logger.error(f"Error saving evaluation report: {str(e)}")

def generate_markdown_report(evaluation_report):
    """
    Generate a markdown report from the evaluation data.
    
    Args:
        evaluation_report (dict): The evaluation report data
        
    Returns:
        str: Markdown formatted report
    """
    logger.debug("Generating markdown evaluation report")
    
    metrics = evaluation_report["metrics"]
    results = evaluation_report["results"]
    timestamp = evaluation_report["timestamp"]
    
    md = f"# Medical Knowledge Graph Evaluation Report\n\n"
    md += f"Generated: {timestamp}\n\n"
    
    # Metrics section
    md += "## Summary Metrics\n\n"
    md += f"- **Number of Questions**: {metrics['num_questions']}\n"
    md += f"- **Questions Evaluated**: {metrics['num_evaluated']}\n"
    md += f"- **Average Score**: {metrics['average_score']:.2f}\n"
    md += f"- **Total Score**: {metrics['total_score']:.2f}\n\n"
    
    # Results section
    md += "## Individual Question Results\n\n"
    
    for idx, result in enumerate(results):
        md += f"### Question {idx+1}: {result['question']}\n\n"
        
        md += f"**Entities**: {', '.join(result['entities']) if result['entities'] else 'None'}\n\n"
        md += f"**Query Type**: {result['query_type']}\n\n"
        
        md += "**Query**:\n```cypher\n"
        md += f"{result['query']}\n"
        md += "```\n\n"
        
        md += "**System Answer**:\n"
        md += f"{result['system_answer']}\n\n"
        
        if result['expected_answer']:
            md += "**Expected Answer**:\n"
            md += f"{result['expected_answer']}\n\n"
            
            md += f"**Score**: {result['score']:.2f}\n\n"
            md += f"**Explanation**: {result['explanation']}\n\n"
        else:
            md += "*No expected answer provided for evaluation.*\n\n"
        
        md += "---\n\n"
    
    logger.debug("Markdown report generation complete")
    return md 