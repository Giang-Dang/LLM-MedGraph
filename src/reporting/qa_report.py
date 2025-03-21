"""
Question-Answer pair evaluation and reporting module.
"""
import os
import json
from datetime import datetime
from ..config import get_logger

# Get module-specific logger
logger = get_logger("reporting.qa_report")

def process_qa_pairs(qa_pairs, report_filename):
    """
    Process a list of question-answer pairs and generate a Markdown report.
    
    Args:
        qa_pairs (list): List of dictionaries containing questions and expected answers
        report_filename (str): Filename for the evaluation report
        
    Returns:
        str: Path to the generated report file
    """
    logger.info(f"Processing {len(qa_pairs)} question-answer pairs")
    
    # Ensure the file extension is .md
    if not report_filename.endswith('.md'):
        report_filename += '.md'
    
    try:
        # Try to import the evaluation module
        try:
            from ..evaluation.evaluator import evaluate_question_answer_pairs
            
            # Run the evaluation
            eval_results = evaluate_question_answer_pairs(qa_pairs, report_filename)
            
            # Generate a more readable Markdown table report
            generate_markdown_table_report(eval_results, report_filename)
            
        except ImportError as e:
            logger.warning(f"Could not import evaluator module: {str(e)}")
            logger.info("Generating a simplified report without evaluation")
            
            # Create a simplified report directly
            generate_simplified_report(qa_pairs, report_filename)
            
        logger.info(f"Report generated successfully as {report_filename}")
        return report_filename
    
    except Exception as e:
        logger.error(f"Error processing question-answer pairs: {str(e)}", exc_info=True)
        return None

def generate_simplified_report(qa_pairs, report_filename):
    """
    Generate a simplified Markdown report without evaluation.
    
    Args:
        qa_pairs (list): List of dictionaries containing questions and expected answers
        report_filename (str): Filename for the report
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(report_filename) if os.path.dirname(report_filename) else '.', exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        # Write report header
        f.write("# Question-Answer Pairs (No Evaluation)\n\n")
        f.write(f"Generated: {timestamp}\n\n")
        f.write(f"Total Questions: {len(qa_pairs)}\n\n")
        
        # Write disclaimer
        f.write("> **Note**: This report contains only the question-answer pairs without evaluation.\n")
        f.write("> Evaluation could not be performed because the Neo4j database connection was not available.\n\n")
        
        # Write QA pairs table
        f.write("## Question-Answer Pairs\n\n")
        f.write("| No. | Question | Expected Answer |\n")
        f.write("|-----|----------|----------------|\n")
        
        for idx, qa_pair in enumerate(qa_pairs, 1):
            # Format the question and answer for Markdown
            question = qa_pair['question'].replace("\n", " ").replace("|", "\\|")
            expected_answer = qa_pair['expected_answer'].replace("\n", "<br>").replace("|", "\\|") if 'expected_answer' in qa_pair else "N/A"
            
            # Write table row
            f.write(f"| {idx} | {question} | {expected_answer} |\n")
            
        # Write detailed section
        f.write("\n## Detailed Question-Answer Pairs\n\n")
        
        for idx, qa_pair in enumerate(qa_pairs, 1):
            f.write(f"### Question {idx}: {qa_pair['question']}\n\n")
            
            if 'expected_answer' in qa_pair and qa_pair['expected_answer']:
                f.write("**Expected Answer**:\n```\n")
                f.write(f"{qa_pair['expected_answer']}\n")
                f.write("```\n\n")
            else:
                f.write("*No expected answer provided.*\n\n")
            
            f.write("---\n\n")

def generate_markdown_table_report(eval_results, report_filename):
    """
    Generate a Markdown report with a table of results.
    
    Args:
        eval_results (dict): Evaluation results from evaluate_question_answer_pairs
        report_filename (str): Filename for the report
    """
    metrics = eval_results["metrics"]
    results = eval_results["results"]
    timestamp = eval_results["timestamp"]
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(report_filename) if os.path.dirname(report_filename) else '.', exist_ok=True)
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        # Write report header
        f.write("# Question-Answer Evaluation Report\n\n")
        f.write(f"Generated: {timestamp}\n\n")
        
        # Write summary metrics
        f.write("## Summary Metrics\n\n")
        f.write(f"- **Number of Questions**: {metrics['num_questions']}\n")
        f.write(f"- **Questions Evaluated**: {metrics['num_evaluated']}\n")
        f.write(f"- **Average Score**: {metrics['average_score']:.2f}\n")
        f.write(f"- **Total Score**: {metrics['total_score']:.2f}\n\n")
        
        # Write results table
        f.write("## Evaluation Results\n\n")
        f.write("| No. | Question | System Answer | Expected Answer | Score | Explanation |\n")
        f.write("|-----|----------|---------------|-----------------|-------|-------------|\n")
        
        for idx, result in enumerate(results, 1):
            # Format the question
            question = result['question'].replace("\n", " ")
            
            # Format the system answer
            system_answer = result['system_answer'].replace("\n", "<br>").replace("|", "\\|")
            
            # Format the expected answer
            expected_answer = result['expected_answer'].replace("\n", "<br>").replace("|", "\\|") if result['expected_answer'] else "N/A"
            
            # Format the score
            score = f"{result['score']:.2f}" if result['score'] is not None else "N/A"
            
            # Format the explanation
            explanation = result['explanation'].replace("\n", "<br>").replace("|", "\\|") if 'explanation' in result else "N/A"
            
            # Write table row
            f.write(f"| {idx} | {question} | {system_answer} | {expected_answer} | {score} | {explanation} |\n")
        
        # Write individual detailed results
        f.write("\n## Detailed Results\n\n")
        
        for idx, result in enumerate(results, 1):
            f.write(f"### Question {idx}: {result['question']}\n\n")
            
            if result['entities']:
                f.write(f"**Entities**: {', '.join(result['entities'])}\n\n")
            
            f.write(f"**Query Type**: {result['query_type']}\n\n")
            
            f.write("**Query**:\n```cypher\n")
            f.write(f"{result['query']}\n")
            f.write("```\n\n")
            
            f.write("**System Answer**:\n```\n")
            f.write(f"{result['system_answer']}\n")
            f.write("```\n\n")
            
            if result['expected_answer']:
                f.write("**Expected Answer**:\n```\n")
                f.write(f"{result['expected_answer']}\n")
                f.write("```\n\n")
                
                f.write(f"**Score**: {result['score']:.2f}\n\n")
                f.write(f"**Explanation**: {result['explanation']}\n\n")
            else:
                f.write("*No expected answer provided for evaluation.*\n\n")
            
            f.write("---\n\n") 