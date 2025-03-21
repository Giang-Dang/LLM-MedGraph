"""
Main entry point for the Medical Knowledge Graph application.
"""
import argparse
import sys
from src.config import (
    EXPECTED_QA_PAIRS, SAMPLE_QUESTIONS, APPLICATION_NAME, 
    EVALUATION_METHODS, DEFAULT_REPORT_FILENAME,
    get_logger
)
from src.evaluation.accuracy import evaluate_responses
from src.reporting.report import generate_report
from src.reporting.qa_report import process_qa_pairs
from src.query.cypher import execute_cypher_query
from src.nlp.llm import generate_response

# Get module-specific logger
logger = get_logger("main")

def parse_args():
    """
    Parse command line arguments.
    
    Returns:
        argparse.Namespace: The parsed arguments
    """
    parser = argparse.ArgumentParser(description=f"{APPLICATION_NAME} CLI")
    
    # Mode selection
    parser.add_argument(
        "--mode", 
        type=str, 
        choices=["interactive", "single", "evaluate", "qa_evaluate"], 
        default="interactive",
        help="Operating mode: interactive (default), single question, or evaluation"
    )
    
    # Question for single mode
    parser.add_argument(
        "--question", 
        type=str, 
        help="Question to answer (required for single mode)"
    )
    
    # Evaluation method
    parser.add_argument(
        "--method", 
        type=str, 
        choices=EVALUATION_METHODS,
        default=EVALUATION_METHODS[0], 
        help="Evaluation method (only for evaluate mode)"
    )
    
    # Report filename
    parser.add_argument(
        "--report", 
        type=str, 
        default=DEFAULT_REPORT_FILENAME,
        help="Filename for evaluation report (only for evaluate mode)"
    )
    
    args = parser.parse_args()
    
    # Validate args
    if args.mode == "single" and not args.question:
        parser.error("--question is required when using --mode single")
    
    logger.info(f"Command-line arguments parsed: mode={args.mode}")
    return args


def interactive_mode(use_graph=True):
    """
    Run the application in interactive mode, allowing users to ask medical questions.
    
    Args:
        use_graph (bool, optional): Whether to use Neo4j for context. Defaults to True.
    """
    logger.info("Starting interactive mode")
    logger.info("Displaying welcome message")
    
    # Display welcome message using standard output (user-facing)
    print("\nMedical Knowledge Graph Query System")
    print("-----------------------------------")
    print("Ask questions about diseases, symptoms, treatments, etc.")
    print("Type 'exit', 'quit', or 'q' to end the session.\n")
    
    while True:
        # Get user question
        user_input = input("\nEnter your question: ")
        
        # Check if user wants to exit
        if user_input.lower() in ["exit", "quit", "q"]:
            logger.info("User requested exit")
            # Display exit message (user-facing)
            print("Exiting. Goodbye!")
            break
        
        # Process the question and generate response
        try:
            logger.info(f"Processing user question: {user_input}")
            if use_graph:
                # Use Neo4j for context
                logger.debug("Using Neo4j for context")
                context = execute_cypher_query(user_input)
                response = generate_response(user_input, use_graph=True, context=context)
            else:
                # Use LLM's intrinsic knowledge
                logger.debug("Using LLM's intrinsic knowledge (no graph)")
                response = generate_response(user_input, use_graph=False)
                
            # Display response (user-facing)
            print("\nAnswer:", response)
            logger.debug(f"Response generated successfully (length: {len(response)})")
            
        except Exception as e:
            error_msg = f"Error processing question: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Display error message (user-facing)
            print(f"\n{error_msg}")


def single_question_mode(question, use_graph=True):
    """
    Answer a single question and return the response.
    
    Args:
        question (str): The question to answer
        use_graph (bool, optional): Whether to use Neo4j for context. Defaults to True.
        
    Returns:
        str: The response to the question
    """
    logger.info(f"Processing single question: {question}")
    try:
        if use_graph:
            # Use Neo4j for context
            logger.debug("Using Neo4j for context")
            context = execute_cypher_query(question)
            response = generate_response(question, use_graph=True, context=context)
        else:
            # Use LLM's intrinsic knowledge
            logger.debug("Using LLM's intrinsic knowledge (no graph)")
            response = generate_response(question, use_graph=False)
            
        # Display question and answer (user-facing)
        print("\nQuestion:", question)
        print("\nAnswer:", response)
        logger.debug(f"Response generated successfully (length: {len(response)})")
        return response
        
    except Exception as e:
        error_msg = f"Error processing question: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Display error message (user-facing)
        print(error_msg)
        return error_msg


def evaluate_mode(method, report_filename=None):
    """
    Run evaluation on sample questions and generate a comparative report.
    
    Args:
        method (str): The evaluation method to use
        report_filename (str, optional): Name of report file to generate. 
                                         If None, generates a filename with timestamp.
    
    Returns:
        str: Path to the generated report file
    """
    logger.info("Starting evaluation mode")
    # Display progress message (user-facing)
    print("\nEvaluating responses for sample questions...")
    print(f"Processing {len(SAMPLE_QUESTIONS)} questions. This might take some time...")
    
    # Run evaluation
    logger.debug("Calling evaluate_responses")
    evaluation_results = evaluate_responses(SAMPLE_QUESTIONS)
    
    # Generate report
    logger.debug("Generating evaluation report")
    report_path = generate_report(evaluation_results, report_filename)
    
    logger.info(f"Evaluation complete. Report saved to: {report_path}")
    # Display completion message (user-facing)
    print(f"\nEvaluation complete. Report saved to: {report_path}")
    return report_path


def qa_evaluate_mode(report_filename):
    """
    Run the question-answer evaluation mode.
    
    Args:
        report_filename (str): Filename for the evaluation report
    """
    logger.info("Starting question-answer evaluation")
    
    print(f"\n{APPLICATION_NAME} - Question Answer Evaluation Mode")
    print("=" * 50)
    
    try:
        # Create question-answer pairs from sample questions
        qa_pairs = EXPECTED_QA_PAIRS
        
        print(f"Evaluating {len(qa_pairs)} question-answer pairs...")
        
        # Process QA pairs and generate the report
        result_file = process_qa_pairs(qa_pairs, report_filename)
        
        if result_file:
            print(f"\nEvaluation complete. Report saved to: {result_file}")
            logger.info(f"Question-answer evaluation completed successfully. Report saved to {result_file}")
        else:
            print("\nEvaluation failed. Check the logs for more information.")
            logger.error("Question-answer evaluation failed to complete")
    
    except Exception as e:
        error_msg = f"Error in question-answer evaluation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\nError: {error_msg}")


def main():
    """
    Main entry point for the application.
    """
    # Parse command line args
    args = parse_args()
    
    try:
        # Determine which mode to run
        if args.mode == "interactive":
            logger.info("Starting interactive mode")
            interactive_mode()
        elif args.mode == "single":
            logger.info(f"Starting single mode with question: {args.question}")
            single_question_mode(args.question)
        elif args.mode == "evaluate":
            logger.info(f"Starting evaluation mode with method: {args.method}")
            evaluate_mode(args.method, args.report)
        elif args.mode == "qa_evaluate":
            logger.info("Starting question-answer evaluation mode")
            qa_evaluate_mode(args.report)
        
        logger.info("Application exiting normally")
    except Exception as e:
        error_msg = f"Unhandled exception in main: {str(e)}"
        logger.error(error_msg, exc_info=True)
        print(f"\nError: {error_msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
