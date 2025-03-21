"""
Main entry point for the Medical Knowledge Graph application.
"""
import argparse
from src.config import SAMPLE_QUESTIONS, get_logger
from src.db.connection import close_driver
from src.evaluation.accuracy import evaluate_responses
from src.reporting.report import generate_report
from src.query.cypher import execute_cypher_query
from src.nlp.llm import generate_response

# Get module-specific logger
logger = get_logger("main")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Medical Knowledge Graph Query System")
    parser.add_argument(
        "--mode", 
        choices=["interactive", "evaluate", "single"], 
        default="interactive",
        help="Running mode: interactive chat, evaluate on sample questions, or single question"
    )
    parser.add_argument(
        "--question", 
        type=str,
        help="Single question to answer (only used in single mode)"
    )
    parser.add_argument(
        "--report", 
        type=str,
        help="Report filename (for evaluate mode)"
    )
    parser.add_argument(
        "--use_graph", 
        action="store_true",
        help="Whether to use graph database for retrieving context"
    )
    
    return parser.parse_args()


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


def evaluate_mode(report_filename=None):
    """
    Run evaluation on sample questions and generate a comparative report.
    
    Args:
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


def main():
    """Main function to run the application."""
    # Parse command line arguments
    args = parse_args()
    
    logger.info(f"Starting Medical Knowledge Graph application in {args.mode} mode")
    logger.debug(f"Command line arguments: {args}")
    
    try:
        # Run in the selected mode
        if args.mode == "interactive":
            interactive_mode(use_graph=args.use_graph)
        elif args.mode == "single":
            if not args.question:
                logger.error("No question provided for single mode")
                # Display error message (user-facing)
                print("Error: --question is required in single mode.")
                return
            single_question_mode(args.question, use_graph=args.use_graph)
        elif args.mode == "evaluate":
            evaluate_mode(args.report)
    finally:
        # Ensure the Neo4j driver is closed properly
        logger.debug("Cleaning up resources")
        close_driver()
    
    logger.info("Application exiting normally")


if __name__ == "__main__":
    main()
