import os
import csv
import logging
from datetime import datetime
from langsmith import Client

def save_langsmith_stats(task_id=None, project_name=None, output_path=None):
    """
    Fetches all LangSmith trace statistics for the given project and saves them to a CSV file.
    Assumes that the LANGCHAIN-related env vars are populated correctly in .env
    """
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        logging.info("LangSmith API key not found. Skipping stats export.")
        return None

    if not output_path:
        if task_id:
            output_path = f"outputs/{task_id}_langsmith_stats.csv"
        else:
            output_path = "outputs/langsmith_stats.csv"

    try:
        client = Client()
        project_name = project_name or os.environ.get("LANGCHAIN_PROJECT", "default")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        runs = list(client.list_runs(project_name=project_name, limit=100))
        
        if not runs:
            logging.info(f"No LangSmith runs found for project: {project_name}")
            return None

        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                "Run ID", "Name", "Run Type", "Start Time", "End Time", 
                "Latency (ms)", "Total Tokens", "Prompt Tokens", 
                "Completion Tokens", "Total Cost"
            ])
            
            for run in runs:
                start_time = run.start_time
                end_time = run.end_time
                latency = (end_time - start_time).total_seconds() * 1000 if end_time and start_time else 0
                
                total_tokens = getattr(run, 'total_tokens', 0) or 0
                prompt_tokens = getattr(run, 'prompt_tokens', 0) or 0
                completion_tokens = getattr(run, 'completion_tokens', 0) or 0
                total_cost = getattr(run, 'total_cost', 0) or 0
                
                writer.writerow([
                    run.id,
                    run.name,
                    run.run_type,
                    start_time.isoformat() if start_time else "",
                    end_time.isoformat() if end_time else "",
                    f"{latency:.2f}",
                    total_tokens,
                    prompt_tokens,
                    completion_tokens,
                    f"{total_cost:.6f}"
                ])
        
        print(f"LangSmith stats saved to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error saving LangSmith stats: {e}")
        return None
