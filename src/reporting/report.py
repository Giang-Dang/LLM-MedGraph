"""
Report generation module for evaluation results.
"""
from datetime import datetime
from ..config import get_logger

# Get module-specific logger
logger = get_logger("reporting.report")

def generate_report(evaluations, filename=None):
    """
    Generate a Markdown report from the evaluation results with comparison tables.
    
    Args:
        evaluations (list or dict): Evaluation results from evaluate_responses
        filename (str, optional): Output filename. If None, generates a timestamped filename
        
    Returns:
        str: Path to the generated report file
    """
    # Generate filename with current date and time if not provided
    if filename is None:
        current_time = datetime.now().strftime("%d-%m-%y_%H-%M")
        filename = f"report_{current_time}.md"
    
    # Ensure evaluations is a list even for single evaluations
    if not isinstance(evaluations, list):
        evaluations = [evaluations]
    
    try:
        logger.info(f"Generating evaluation report with {len(evaluations)} questions")
        
        with open(filename, "w", encoding="utf-8") as f:
            # Write report header
            _write_report_header(f, evaluations)
            
            # Write factual accuracy comparison
            accuracy_data = _calculate_accuracy_data(evaluations)
            _write_accuracy_comparison(f, evaluations, accuracy_data)
            
            # Write summary section
            _write_summary_section(f, accuracy_data)
            
            # Write comprehensive comparison table
            _write_comprehensive_comparison(f, evaluations)
            
            # Write Neo4j queries diagnostic table
            _write_neo4j_queries_diagnostics(f, evaluations)
                
        logger.info(f"Report generated successfully as {filename}")
        return filename
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        return None


def _write_report_header(file, evaluations):
    """Write the report header section to the file."""
    file.write("# Medical Evaluation Report\n\n")
    file.write(f"Generated on: {datetime.now().strftime('%d-%m-%Y at %H:%M')}\n\n")
    file.write(f"Total questions evaluated: {len(evaluations)}\n\n")


def _calculate_accuracy_data(evaluations):
    """
    Calculate accuracy statistics from evaluations.
    
    Args:
        evaluations (list): List of evaluation results
        
    Returns:
        dict: Dictionary containing accuracy statistics
    """
    # Initialize totals
    total_without_db = 0
    total_with_db = 0
    question_count = len(evaluations)
    
    # Calculate totals
    for eval_item in evaluations:
        total_without_db += eval_item.get("accuracy_without_graph", 0)
        total_with_db += eval_item.get("accuracy_with_graph", 0)
    
    # Calculate averages
    avg_without_db = total_without_db / max(1, question_count)  # Avoid division by zero
    avg_with_db = total_with_db / max(1, question_count)        # Avoid division by zero
    improvement = avg_with_db - avg_without_db
    
    return {
        "total_without_db": total_without_db,
        "total_with_db": total_with_db,
        "question_count": question_count,
        "avg_without_db": avg_without_db,
        "avg_with_db": avg_with_db,
        "improvement": improvement
    }


def _write_accuracy_comparison(file, evaluations, accuracy_data):
    """Write the factual accuracy comparison table to the file."""
    file.write("## Factual Accuracy Comparison\n\n")
    file.write("| No. | Question | Without Neo4j | With Neo4j |\n")
    file.write("|-----|----------|---------------|------------|\n")
    
    for idx, eval_item in enumerate(evaluations, 1):
        accuracy_without = eval_item.get("accuracy_without_graph", 0)
        accuracy_with = eval_item.get("accuracy_with_graph", 0)
        
        # Format accuracies as percentages
        accuracy_without_str = f"{accuracy_without:.2%}"
        accuracy_with_str = f"{accuracy_with:.2%}"
        
        # Write table row
        file.write(f"| {idx} | {eval_item['question']} | {accuracy_without_str} | {accuracy_with_str} |\n")


def _write_summary_section(file, accuracy_data):
    """Write the summary section to the file."""
    file.write("\n## Summary\n\n")
    file.write(f"Total Questions: {accuracy_data['question_count']}\n\n")
    file.write(f"Average Factual Accuracy without Neo4j: {accuracy_data['avg_without_db']:.2%}\n\n")
    file.write(f"Average Factual Accuracy with Neo4j: {accuracy_data['avg_with_db']:.2%}\n\n")
    file.write(f"Overall Improvement: {accuracy_data['improvement']:.2%}\n\n")


def _write_comprehensive_comparison(file, evaluations):
    """Write the comprehensive comparison table to the file."""
    file.write("## Comprehensive Comparison\n\n")
    file.write("| No. | Original Question | Query Type | Without Neo4j |  With Neo4j |\n")
    file.write("|-----|-------------------|------------|---------------|-------------|\n")

    for idx, eval_item in enumerate(evaluations, 1):
        # Format the cells for the table
        without_neo4j_cell, with_neo4j_cell = _format_comparison_cells(eval_item)
        
        # Get the query type
        query_type = eval_item.get("query_type", "general")
        
        # Write formatted row to markdown table
        file.write(f"| {idx} | {eval_item['question']} | {query_type} | {without_neo4j_cell} | {with_neo4j_cell} |\n")


def _format_comparison_cells(eval_item):
    """
    Format the cells for the comprehensive comparison table.
    
    Args:
        eval_item (dict): Evaluation item containing prompt and response data
        
    Returns:
        tuple: Formatted cells for without Neo4j and with Neo4j
    """
    # Get responses
    response_without = _clean_response_text(eval_item.get("response_without_graph", ""))
    response_with = _clean_response_text(eval_item.get("response_with_graph", ""))
    
    # Format prompts for readability in markdown
    prompt_without = eval_item.get("prompt_without_graph", "").replace("\n", "<br>")
    prompt_with = eval_item.get("prompt_with_graph", "").replace("\n", "<br>")
    
    # Create combined cells with both prompt and response
    without_neo4j_cell = f"**Prompt:**<br>{prompt_without}<br><br>**Response:**<br>{response_without}"
    with_neo4j_cell = f"**Prompt:**<br>{prompt_with}<br><br>**Response:**<br>{response_with}"
    
    return without_neo4j_cell, with_neo4j_cell


def _write_neo4j_queries_diagnostics(file, evaluations):
    """Write a table containing Neo4j query diagnostics for each question."""
    file.write("\n## Neo4j Query Diagnostics\n\n")
    file.write("| No. | Question | Query Type | Reverse Lookup | Context Query | Context Result | Entity Extraction Results |\n")
    file.write("|-----|----------|------------|----------------|---------------|---------------|--------------------------|\n")
    
    # Reference the query templates defined in the application
    forward_query_templates = {
        "symptoms": "Disease → Symptoms",
        "treatments": "Disease → Treatments",
        "prevention": "Disease → Prevention Methods",
        "risk_factors": "Disease → Risk Factors",
        "age_groups": "Disease → Age Groups",
        "gender": "Disease → Gender Distribution",
        "prevalence": "Disease → Prevalence Distribution",
        "general": "Disease → General Information"
    }
    
    reverse_query_templates = {
        "symptoms": "Symptom → Diseases",
        "treatments": "Treatment → Diseases",
        "prevention": "Prevention Method → Diseases",
        "risk_factors": "Risk Factor → Diseases",
        "age_groups": "Age Group → Diseases",
        "gender": "Gender → Diseases"
    }
    
    for idx, eval_item in enumerate(evaluations, 1):
        question = eval_item['question']
        query_type = eval_item.get('query_type', 'general')
        is_reverse = eval_item.get('is_reverse_lookup', False)
        
        # Extract context from prompt with graph
        context = ""
        prompt_with_graph = eval_item.get('prompt_with_graph', '')
        if 'Context:' in prompt_with_graph:
            context_parts = prompt_with_graph.split('Context:')
            if len(context_parts) > 1:
                context_block = context_parts[1].split('Based ONLY')[0].strip()
                context = context_block.replace('\n', '<br>')
        
        # Extract entities from question
        from ..nlp.entity_extraction import analyze_question
        entities, _ = analyze_question(question)
        entities_str = ', '.join(entities) if entities else 'None detected'
        
        # Format the reverse lookup status
        reverse_status = "Yes" if is_reverse else "No"
        
        # Determine query template used
        query_template = ""
        if is_reverse:
            if query_type in reverse_query_templates:
                query_template = reverse_query_templates[query_type]
            else:
                query_template = "No suitable reverse template"
        else:
            if query_type in forward_query_templates:
                query_template = forward_query_templates[query_type]
            else:
                query_template = "General query template"
        
        # Write row
        file.write(f"| {idx} | {question} | {query_type} | {reverse_status} | {query_template} | {context} | Entities: {entities_str} |\n")


def _clean_response_text(response_text):
    """
    Clean and format response text for display in the report.
    
    Args:
        response_text (str): Raw response text
        
    Returns:
        str: Cleaned response text
    """
    # Extract content between response=' and ' if present
    if "response='" in response_text:
        response_text = response_text.split("response='")[1].split("'")[0]
    
    # Clean responses for markdown
    return response_text.replace("\n", " ").replace("*", "").replace("---", "") 