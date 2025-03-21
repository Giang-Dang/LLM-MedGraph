"""
Question-Answer pair evaluation and reporting module.
"""
import os
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
        f.write("# Neo4j Question-Answer Evaluation Report\n\n")
        f.write(f"Generated: {timestamp}\n\n")
        
        # Write summary metrics
        f.write("## Summary Metrics\n\n")
        f.write(f"- **Number of Questions**: {metrics['num_questions']}\n")
        
        # With Neo4j metrics
        f.write("### With Neo4j\n")
        f.write(f"- **Questions Evaluated**: {metrics['num_with_neo4j_evaluated']}\n")
        f.write(f"- **Average Score**: {metrics['average_with_neo4j_score']:.2f}\n")
        f.write(f"- **Total Score**: {metrics['total_with_neo4j_score']:.2f}\n\n")
        
        # Without Neo4j metrics
        f.write("### Without Neo4j\n")
        f.write(f"- **Questions Evaluated**: {metrics['num_without_neo4j_evaluated']}\n")
        f.write(f"- **Average Score**: {metrics['average_without_neo4j_score']:.2f}\n")
        f.write(f"- **Total Score**: {metrics['total_without_neo4j_score']:.2f}\n\n")
        
        # Comparison summary
        diff = metrics['average_with_neo4j_score'] - metrics['average_without_neo4j_score']
        f.write("### Comparison\n")
        f.write(f"- **Score Difference (Neo4j vs. No Neo4j)**: {diff:.2f} ({'+' if diff >= 0 else ''}{diff*100:.2f}%)\n\n")
        
        # Write results table
        f.write("## Evaluation Results\n\n")
        f.write("| No. | Question | With Neo4j Answer | Without Neo4j Answer | Expected Answer | With Neo4j Score | Without Neo4j Score |\n")
        f.write("|-----|----------|-------------------|----------------------|-----------------|------------------|--------------------|\n")
        
        for idx, result in enumerate(results, 1):
            # Format the question
            question = result['question'].replace("\n", " ").replace("|", "\\|")
            
            # Format the system answers
            with_neo4j_answer = result['with_neo4j_answer'].replace("\n", "<br>").replace("|", "\\|") if result['with_neo4j_answer'] else "N/A"
            if len(with_neo4j_answer) > 80:
                with_neo4j_answer = with_neo4j_answer[:77] + "..."
                
            without_neo4j_answer = result['without_neo4j_answer'].replace("\n", "<br>").replace("|", "\\|") if result['without_neo4j_answer'] else "N/A"
            if len(without_neo4j_answer) > 80:
                without_neo4j_answer = without_neo4j_answer[:77] + "..."
            
            # Format the expected answer
            expected_answer = result['expected_answer'].replace("\n", "<br>").replace("|", "\\|") if result['expected_answer'] else "N/A"
            if len(expected_answer) > 80:
                expected_answer = expected_answer[:77] + "..."
            
            # Format the scores
            with_neo4j_score = f"{result['with_neo4j_score']:.2f}" if result['with_neo4j_score'] is not None else "N/A"
            without_neo4j_score = f"{result['without_neo4j_score']:.2f}" if result['without_neo4j_score'] is not None else "N/A"
            
            # Write table row
            f.write(f"| {idx} | {question} | {with_neo4j_answer} | {without_neo4j_answer} | {expected_answer} | {with_neo4j_score} | {without_neo4j_score} |\n")
        
        # Write detailed results section
        f.write("\n## Detailed Results\n\n")
        
        for idx, result in enumerate(results, 1):
            f.write(f"### Question {idx}: {result['question']}\n\n")
            
            if result['entities']:
                f.write(f"**Entities**: {', '.join(result['entities'])}\n\n")
            
            f.write(f"**Query Type**: {result['query_type']}\n\n")
            
            f.write("**Query**:\n```cypher\n")
            f.write(f"{result['query']}\n")
            f.write("```\n\n")
            
            # With Neo4j section
            f.write("#### With Neo4j\n\n")
            f.write("**System Answer**:\n```\n")
            f.write(f"{result['with_neo4j_answer']}\n")
            f.write("```\n\n")
            
            if result['with_neo4j_score'] is not None:
                f.write(f"**Score**: {result['with_neo4j_score']:.2f}\n\n")
                if 'with_neo4j_explanation' in result:
                    f.write(f"**Explanation**: {result['with_neo4j_explanation']}\n\n")
            
            # Without Neo4j section
            f.write("#### Without Neo4j\n\n")
            f.write("**System Answer**:\n```\n")
            f.write(f"{result['without_neo4j_answer']}\n")
            f.write("```\n\n")
            
            if result['without_neo4j_score'] is not None:
                f.write(f"**Score**: {result['without_neo4j_score']:.2f}\n\n")
                if 'without_neo4j_explanation' in result:
                    f.write(f"**Explanation**: {result['without_neo4j_explanation']}\n\n")
            
            # Expected answer
            if result['expected_answer']:
                f.write("#### Expected Answer\n\n")
                f.write("```\n")
                f.write(f"{result['expected_answer']}\n")
                f.write("```\n\n")
            else:
                f.write("*No expected answer provided for evaluation.*\n\n")
            
            f.write("---\n\n")