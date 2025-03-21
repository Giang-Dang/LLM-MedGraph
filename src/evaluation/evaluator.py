"""
Medical knowledge graph evaluator module.
"""
import json
import ollama
from datetime import datetime
from difflib import SequenceMatcher
# Change relative imports to absolute imports
from src.config import LLM_EVALUATION_MODEL, get_logger
from src.nlp.entity_extraction import analyze_question
from src.nlp.llm import generate_response
from src.query.query_generator import create_query_with_llm, execute_query

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
    total_with_neo4j_score = 0
    total_without_neo4j_score = 0
    
    for idx, qa_pair in enumerate(qa_pairs):
        question = qa_pair["question"]
        expected_answer = qa_pair["expected_answer"] if "expected_answer" in qa_pair else None
        
        # Process the question
        logger.info(f"Processing question {idx+1}/{len(qa_pairs)}: {question}")
        entities, query_type = analyze_question(question)
        
        # Generate and execute query
        query = create_query_with_llm(entities, query_type)
        query_results = execute_query(query)
        
        # Check if query execution returned an error
        if query_results and "error" in query_results[0]:
            with_neo4j_answer = f"Error: {query_results[0]['error']}"
            with_neo4j_score = 0
            with_neo4j_explanation = "Query execution failed"
            logger.warning(f"Query execution failed: {query_results[0]['error']}")
        else:
            # Format the answer based on query results
            with_neo4j_answer = generate_response(question, use_graph=True, context=query_results)
            without_neo4j_answer = generate_response(question, use_graph=False)
            
            # If expected answer is provided, evaluate the system answer
            if expected_answer:
                with_neo4j_score, with_neo4j_explanation = evaluate_answer(with_neo4j_answer, expected_answer)
                without_neo4j_score, without_neo4j_explanation = evaluate_answer(without_neo4j_answer, expected_answer)
                logger.debug(f"Answer evaluation score: {with_neo4j_score}, explanation: {with_neo4j_explanation}")
            else:
                with_neo4j_score = None
                with_neo4j_explanation = "No expected answer provided"
                without_neo4j_score = None
                without_neo4j_explanation = "No expected answer provided"
                logger.debug("No expected answer provided for evaluation")
        
        # Store the result
        result = {
            "question": question,
            "entities": entities,
            "query_type": query_type,
            "query": query,
            "query_results": query_results,
            "with_neo4j_answer": with_neo4j_answer,
            "without_neo4j_answer": without_neo4j_answer,
            "expected_answer": expected_answer,
            "with_neo4j_score": with_neo4j_score,
            "without_neo4j_score": without_neo4j_score,
            "with_neo4j_explanation": with_neo4j_explanation,
            "without_neo4j_explanation": without_neo4j_explanation
        }
        
        results.append(result)
        
        if with_neo4j_score is not None:
            total_with_neo4j_score += with_neo4j_score

        if without_neo4j_score is not None:
            total_without_neo4j_score += without_neo4j_score
    
    # Calculate overall metrics
    num_with_neo4j_evaluated = sum(1 for r in results if r["with_neo4j_score"] is not None)
    num_without_neo4j_evaluated = sum(1 for r in results if r["without_neo4j_score"] is not None)
    average_with_neo4j_score = total_with_neo4j_score / num_with_neo4j_evaluated if num_with_neo4j_evaluated > 0 else 0
    average_without_neo4j_score = total_without_neo4j_score / num_without_neo4j_evaluated if num_without_neo4j_evaluated > 0 else 0
    
    logger.info(f"Evaluation complete. Average score: {average_with_neo4j_score:.2f}, Total score: {total_with_neo4j_score:.2f}")
    logger.info(f"Evaluation complete. Average score: {average_without_neo4j_score:.2f}, Total score: {total_without_neo4j_score:.2f}")
    
    # Generate the report
    evaluation_report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": {
            "num_questions": len(qa_pairs),
            "num_with_neo4j_evaluated": num_with_neo4j_evaluated,
            "average_with_neo4j_score": average_with_neo4j_score,
            "total_with_neo4j_score": total_with_neo4j_score,
            "num_without_neo4j_evaluated": num_without_neo4j_evaluated,
            "average_without_neo4j_score": average_without_neo4j_score,
            "total_without_neo4j_score": total_without_neo4j_score
        },
        "results": results
    }
    
    # Save the report
    if report_filename:
        save_evaluation_report(evaluation_report, report_filename)
    
    return evaluation_report

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
            model=LLM_EVALUATION_MODEL,
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
        
        logger.info(f"LLM evaluation ({LLM_EVALUATION_MODEL}) score: {score:.2f}")
        logger.debug(f"LLM evaluation ({LLM_EVALUATION_MODEL}) explanation: {explanation}")
        
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
        evaluation_report (dict): The evaluation report data containing results from evaluate_question_answer_pairs
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
        evaluation_report (dict): The evaluation report data containing results with and without Neo4j
        
    Returns:
        str: Markdown formatted report
    """
    logger.debug("Generating markdown evaluation report")
    
    metrics = evaluation_report["metrics"]
    results = evaluation_report["results"]
    timestamp = evaluation_report["timestamp"]
    
    md = f"# Neo4j Question-Answer Evaluation Report\n\n"
    md += f"Generated: {timestamp}\n\n"
    
    # Metrics section
    md += "## Summary Metrics\n\n"
    md += f"- **Number of Questions**: {metrics['num_questions']}\n"
    
    # With Neo4j metrics
    md += "### With Neo4j\n"
    md += f"- **Questions Evaluated**: {metrics['num_with_neo4j_evaluated']}\n"
    md += f"- **Average Score**: {metrics['average_with_neo4j_score']:.2f}\n"
    md += f"- **Total Score**: {metrics['total_with_neo4j_score']:.2f}\n\n"
    
    # Without Neo4j metrics
    md += "### Without Neo4j\n"
    md += f"- **Questions Evaluated**: {metrics['num_without_neo4j_evaluated']}\n"
    md += f"- **Average Score**: {metrics['average_without_neo4j_score']:.2f}\n"
    md += f"- **Total Score**: {metrics['total_without_neo4j_score']:.2f}\n\n"
    
    # Comparison summary
    diff = metrics['average_with_neo4j_score'] - metrics['average_without_neo4j_score']
    md += "### Comparison\n"
    md += f"- **Score Difference (Neo4j vs. No Neo4j)**: {diff:.2f} ({'+' if diff >= 0 else ''}{diff*100:.2f}%)\n\n"
    
    # Add a summary table of all results
    md += "## Evaluation Results\n\n"
    md += "| No. | Question | With Neo4j Answer | Without Neo4j Answer | Expected Answer | With Neo4j Score | Without Neo4j Score |\n"
    md += "|-----|----------|-------------------|----------------------|-----------------|------------------|--------------------|\n"
    
    for idx, result in enumerate(results):
        # Truncate and format answers for table display
        with_neo4j_answer = result['with_neo4j_answer'].replace('\n', '<br>') if result['with_neo4j_answer'] else "N/A"
        if len(with_neo4j_answer) > 80:
            with_neo4j_answer = with_neo4j_answer[:77] + "..."
            
        without_neo4j_answer = result['without_neo4j_answer'].replace('\n', '<br>') if result['without_neo4j_answer'] else "N/A"
        if len(without_neo4j_answer) > 80:
            without_neo4j_answer = without_neo4j_answer[:77] + "..."
            
        exp_answer = result['expected_answer'].replace('\n', '<br>') if result['expected_answer'] else "N/A"
        if len(exp_answer) > 80:
            exp_answer = exp_answer[:77] + "..."
        
        with_neo4j_score = f"{result['with_neo4j_score']:.2f}" if result['with_neo4j_score'] is not None else "N/A"
        without_neo4j_score = f"{result['without_neo4j_score']:.2f}" if result['without_neo4j_score'] is not None else "N/A"
        
        md += f"| {idx+1} | {result['question']} | {with_neo4j_answer} | {without_neo4j_answer} | {exp_answer} | {with_neo4j_score} | {without_neo4j_score} |\n"
    
    # Detailed Results section
    md += "\n## Detailed Results\n\n"
    
    for idx, result in enumerate(results):
        md += f"### Question {idx+1}: {result['question']}\n\n"
        
        md += f"**Entities**: {', '.join(result['entities']) if result['entities'] else 'None'}\n\n"
        md += f"**Query Type**: {result['query_type']}\n\n"
        
        md += "**Query**:\n```cypher\n"
        md += f"{result['query']}\n"
        md += "```\n\n"
        
        # With Neo4j section
        md += "#### With Neo4j\n\n"
        md += "**System Answer**:\n```\n"
        md += f"{result['with_neo4j_answer']}\n"
        md += "```\n\n"
        
        if result['with_neo4j_score'] is not None:
            md += f"**Score**: {result['with_neo4j_score']:.2f}\n\n"
            if 'with_neo4j_explanation' in result:
                md += f"**Explanation**: {result['with_neo4j_explanation']}\n\n"
        
        # Without Neo4j section
        md += "#### Without Neo4j\n\n"
        md += "**System Answer**:\n```\n"
        md += f"{result['without_neo4j_answer']}\n"
        md += "```\n\n"
        
        if result['without_neo4j_score'] is not None:
            md += f"**Score**: {result['without_neo4j_score']:.2f}\n\n"
            if 'without_neo4j_explanation' in result:
                md += f"**Explanation**: {result['without_neo4j_explanation']}\n\n"
        
        # Expected answer
        if result['expected_answer']:
            md += "#### Expected Answer\n\n"
            md += "```\n"
            md += f"{result['expected_answer']}\n"
            md += "```\n\n"
        else:
            md += "*No expected answer provided for evaluation.*\n\n"
        
        md += "---\n\n"
    
    logger.debug("Markdown report generation complete")
    return md 