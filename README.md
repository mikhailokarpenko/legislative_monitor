# 🏛️ Legislative Monitoring Service

This project implements a Legislative Monitoring Service designed to track cryptocurrency-related legislation using the OpenStates API. It generates compliance alerts for crypto compliance officers, leveraging an LLM (Large Language Model) for summarization and analysis. The workflow is orchestrated using Apache Airflow.

### Features

- **Legislative Monitoring**: Fetches cryptocurrency-related bills from the OpenStates API.
- **LLM-Powered Analysis**: Utilizes an LLM (via `llm_client.py`) to summarize bill content and generate compliance alerts.
- **Airflow Orchestration**: An Apache Airflow DAG (`dags/legislative_monitor_dag.py`) automates the process of fetching, processing, and generating alerts daily.
- **Compliance Alert Generation**: Produces structured compliance alerts with details like summary, deadline, action required, and severity.

### How to get Started?

1.  **Clone the GitHub repository**:
    ```bash
    git clone https://github.com/your-username/ML-OPS-PROJECT.git
    cd ML-OPS-PROJECT
    ```

2.  **Install the required dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Environment Variables**:
    Create a `.env` file in the project root with the following:
    ```
    OPENSTATES_KEY=your_openstates_api_key
    OPENAI_API_KEY=your_openai_api_key # Or your LLM API key if using a different provider
    ```
    *Note*: The `OPENAI_API_KEY` is used by `llm_client.py` which is configured to work with OpenAI-compatible APIs, including local Ollama instances.

4.  **Run with Airflow (Recommended for Production)**:
    This project is designed to run as an Airflow DAG.
    -   Ensure you have Apache Airflow set up.
    -   Place `LegislativeMonitor.py` and `llm_client.py` in your Airflow `dags` folder or ensure they are in your `PYTHONPATH`.
    -   The `dags/legislative_monitor_dag.py` will be automatically picked up by Airflow.
    -   You can trigger the `legislative_monitor` DAG manually or wait for its daily schedule.

5.  **Run Locally (for Development/Testing)**:
    You can run the `LegislativeMonitor.py` script directly for testing purposes:
    ```bash
    python LegislativeMonitor.py
    ```
    This will fetch bills and print the generated alerts to the console.
