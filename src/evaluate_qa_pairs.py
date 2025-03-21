"""
Script to evaluate question-answer pairs and generate a Markdown report.
"""
import os
import json
from datetime import datetime
from src.config import SAMPLE_QUESTIONS, EXPECTED_QA_PAIRS, get_logger
from src.reporting.qa_report import process_qa_pairs

# Get module-specific logger
logger = get_logger("evaluate_qa_pairs")

def main():
    """
    Main function to run the evaluation and generate the report.
    """
    logger.info("Starting question-answer pair evaluation")
    
    # Create the output directory if it doesn't exist
    output_dir = "evaluations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = os.path.join(output_dir, f"qa_evaluation_{timestamp}.md")
    
    qa_pairs = EXPECTED_QA_PAIRS
    
    # Process QA pairs and generate report
    result_file = process_qa_pairs(qa_pairs, report_filename)
    
    if result_file:
        logger.info(f"Evaluation complete. Report saved to {result_file}")
        
        # Print summary information
        print(f"\nEvaluation of {len(qa_pairs)} question-answer pairs completed successfully.")
        print(f"Report saved to: {result_file}")
    else:
        logger.error("Evaluation failed to complete.")
        print("\nEvaluation failed. Check the logs for more information.")

if __name__ == "__main__":
    main() 