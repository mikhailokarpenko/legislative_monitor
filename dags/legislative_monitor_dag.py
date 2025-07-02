#!/usr/bin/env python3
"""
Airflow DAG for Legislative Monitoring Service

This DAG orchestrates the legislative monitoring workflow:
1. Fetch bills from OpenStates API
2. Process bill content
3. Generate compliance alerts
4. Store results
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import json
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.utils.task_group import TaskGroup

# Import your LegislativeMonitor class
# Note: Make sure LegislativeMonitor.py is in your PYTHONPATH or DAGs folder
from LegislativeMonitor import LegislativeMonitor

# Default arguments for the DAG
default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'legislative_monitor',
    default_args=default_args,
    description='Monitor cryptocurrency legislation and generate compliance alerts',
    schedule='@daily',  # Run daily
    catchup=False,
    max_active_runs=1,
    tags=['legislative', 'compliance', 'crypto'],
)

def check_environment_variables(**context):
    """Validate required environment variables are set."""
    required_vars = ['OPENSTATES_KEY', 'OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) and not Variable.get(var, default_var=None):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    print("All required environment variables are set")
    return True

def initialize_monitor(**context):
    """Initialize the LegislativeMonitor instance."""
    try:
        monitor = LegislativeMonitor()
        # Test the connection
        print("LegislativeMonitor initialized successfully")
        return "monitor_initialized"
    except Exception as e:
        raise Exception(f"Failed to initialize LegislativeMonitor: {e}")

def fetch_bills_task(**context):
    """Fetch bills from OpenStates API."""
    monitor = LegislativeMonitor()
    bills = monitor.fetch_bills()
    
    if not bills:
        print("No bills found")
        return []
    
    print(f"Fetched {len(bills)} bills")
    # Store bills in XCom for downstream tasks
    return bills

def process_single_bill(bill_data: Dict, monitor: LegislativeMonitor) -> Dict:
    """Process a single bill and generate compliance alert."""
    bill_id = bill_data.get('id', 'unknown')
    bill_title = bill_data.get('title', 'Unknown')
    
    print(f"Processing bill: {bill_title}")
    
    if not bill_data.get('sources'):
        print(f"No sources found for bill: {bill_title}")
        return {
            'bill_id': bill_id,
            'title': bill_title,
            'status': 'no_sources',
            'alert': None
        }
    
    url = bill_data['sources'][0]['url']
    content = monitor.fetch_bill_content(url)
    
    if not content:
        print(f"No content retrieved for bill: {bill_title}")
        return {
            'bill_id': bill_id,
            'title': bill_title,
            'status': 'no_content',
            'alert': None
        }
    
    alert = monitor.generate_compliance_alert(bill_title, content)
    
    return {
        'bill_id': bill_id,
        'title': bill_title,
        'status': 'processed',
        'alert': alert,
        'url': url
    }

def process_bills_task(**context):
    """Process all fetched bills and generate compliance alerts."""
    # Get bills from previous task
    bills = context['task_instance'].xcom_pull(task_ids='data_fetching.fetch_bills')
    
    if not bills:
        print("No bills to process")
        return []
    
    monitor = LegislativeMonitor()
    processed_bills = []
    
    for bill in bills:
        try:
            result = process_single_bill(bill, monitor)
            processed_bills.append(result)
            print(f"Processed bill: {result['title']} - Status: {result['status']}")
        except Exception as e:
            print(f"Error processing bill {bill.get('title', 'Unknown')}: {e}")
            processed_bills.append({
                'bill_id': bill.get('id', 'unknown'),
                'title': bill.get('title', 'Unknown'),
                'status': 'error',
                'error': str(e),
                'alert': None
            })
    
    return processed_bills

def save_results_task(**context):
    """Save processed results to file or database."""
    processed_bills = context['task_instance'].xcom_pull(task_ids='data_processing.process_bills')
    
    if not processed_bills:
        print("No results to save")
        return
    
    # Create output directory if it doesn't exist
    output_dir = "/opt/airflow/reports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/legislative_alerts_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump(processed_bills, f, indent=2, default=str)
    
    print(f"Results saved to: {output_file}")
    
    # Log summary statistics
    total_bills = len(processed_bills)
    successful = len([b for b in processed_bills if b['status'] == 'processed'])
    errors = len([b for b in processed_bills if b['status'] == 'error'])
    
    print(f"Processing Summary:")
    print(f"  Total bills: {total_bills}")
    print(f"  Successfully processed: {successful}")
    print(f"  Errors: {errors}")
    
    return output_file

def generate_summary_report(**context):
    """Generate a summary report of the monitoring run."""
    processed_bills = context['task_instance'].xcom_pull(task_ids='data_processing.process_bills')
    
    if not processed_bills:
        return "No bills processed"
    
    # Generate summary statistics
    total_bills = len(processed_bills)
    high_severity = len([b for b in processed_bills 
                        if b.get('alert', {}).get('severity') == 'High'])
    medium_severity = len([b for b in processed_bills 
                          if b.get('alert', {}).get('severity') == 'Medium'])
    
    summary = f"""
Legislative Monitor Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total Bills Processed: {total_bills}
High Severity Alerts: {high_severity}
Medium Severity Alerts: {medium_severity}

Bills requiring immediate attention:
"""
    
    for bill in processed_bills:
        alert = bill.get('alert', {})
        if alert.get('severity') == 'High':
            summary += f"- {bill['title']}: {alert.get('action_required', 'Review required')}\n"
    
    # Save summary to file
    output_dir = "/opt/airflow/reports"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/summary_report_{timestamp}.txt"
    
    with open(output_file, 'w') as f:
        f.write(summary)
    
    print(f"Summary report saved to: {output_file}")
    return output_file

# Task definitions
with dag:
    
    # Environment validation
    check_env = PythonOperator(
        task_id='check_environment',
        python_callable=check_environment_variables,
        doc_md="Validate that all required environment variables are set"
    )
    
    # Initialize monitor
    init_monitor = PythonOperator(
        task_id='initialize_monitor',
        python_callable=initialize_monitor,
        doc_md="Initialize the LegislativeMonitor instance and test connections"
    )
    
    # Data fetching task group
    with TaskGroup('data_fetching') as data_fetching_group:
        
        fetch_bills = PythonOperator(
            task_id='fetch_bills',
            python_callable=fetch_bills_task,
            doc_md="Fetch cryptocurrency-related bills from OpenStates API"
        )
    
    # Data processing task group
    with TaskGroup('data_processing') as data_processing_group:
        
        process_bills = PythonOperator(
            task_id='process_bills',
            python_callable=process_bills_task,
            doc_md="Process all fetched bills and generate compliance alerts"
        )
    
    # Output task group
    with TaskGroup('output_generation') as output_group:
        
        save_results = PythonOperator(
            task_id='save_results',
            python_callable=save_results_task,
            doc_md="Save processed results to JSON file"
        )
        
        generate_report = PythonOperator(
            task_id='generate_summary',
            python_callable=generate_summary_report,
            doc_md="Generate and log summary report"
        )
    
    # Cleanup task
    cleanup = BashOperator(
        task_id='cleanup',
        bash_command="""
        echo "Legislative monitoring workflow completed"
        echo "Timestamp: $(date)"
        # Add any cleanup commands here if needed
        """,
        doc_md="Cleanup and final logging"
    )

# Task dependencies
check_env >> init_monitor >> data_fetching_group
data_fetching_group >> data_processing_group >> output_group >> cleanup


