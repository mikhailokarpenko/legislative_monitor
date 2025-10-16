#!/usr/bin/env python3
"""
Legislative Monitoring Service

This script monitors cryptocurrency-related legislation using the OpenStates API
and generates compliance alerts for crypto compliance officers.
"""

import json
import os
import sys
import time
import warnings
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from llm_client import LLMClient

# Suppress XML parsing warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Configuration constants
OPENSTATES_URL = "https://openstates.org/graphql"
REQUEST_TIMEOUT = 20
MAX_TEXT_LENGTH = 8000
RATE_LIMIT_DELAY = 2


class LegislativeMonitor:
    """Monitors legislative changes and generates compliance alerts."""

    def __init__(self):
        """Initialize the legislative monitor with API clients."""
        load_dotenv()

        self.openstates_key = os.getenv("OPENSTATES_KEY")
        if not self.openstates_key:
            raise ValueError("OPENSTATES_KEY environment variable is required")

        self.graphql_client = self._create_graphql_client()
        self.llm = LLMClient()

    def _create_graphql_client(self) -> Client:
        """Create and configure the GraphQL client."""
        return Client(
            transport=RequestsHTTPTransport(
                url=OPENSTATES_URL,
                headers={
                    "X-API-KEY": self.openstates_key,
                    "User-Agent": "LegislativeMonitor/1.0"
                }
            )
        )

    def _execute_graphql_query(self, query: str) -> Optional[Dict]:
        """Execute a GraphQL query with error handling."""
        try:
            return self.graphql_client.execute(gql(query))
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"GraphQL query failed: {e}")
            return None

    def _get_bills_query(self, jurisdiction: str, search_term: str = None, limit: int = 5) -> str:
        """Generate a GraphQL query for bills."""
        search_filter = f', searchQuery: "{search_term}"' if search_term else ""
        return f"""
        query {{
            bills(jurisdiction: "{jurisdiction}", first: {limit}{search_filter}) {{
                edges {{
                    node {{
                        id
                        identifier
                        title
                        sources {{
                            url
                        }}
                    }}
                }}
            }}
        }}
        """

    def fetch_bills(self) -> List[Dict]:
        """Fetch bills from OpenStates API using multiple query strategies."""
        jurisdictions = [
            "ocd-jurisdiction/country:us/state:ca/government",
            "ocd-jurisdiction/country:us/state:al/government"
        ]

        search_terms = ["cryptocurrency", "digital asset", "blockchain"]

        for jurisdiction in jurisdictions:
            # Try jurisdiction without search terms first
            query = self._get_bills_query(jurisdiction)
            result = self._execute_graphql_query(query)

            if result and "bills" in result and "edges" in result["bills"]:
                bills = [edge["node"] for edge in result["bills"]["edges"]]
                if bills:
                    print(f"Retrieved {len(bills)} bills from {jurisdiction}")
                    return bills

            time.sleep(RATE_LIMIT_DELAY)

            # Try with search terms
            for search_term in search_terms:
                query = self._get_bills_query(jurisdiction, search_term, 10)
                result = self._execute_graphql_query(query)

                if result and "bills" in result and "edges" in result["bills"]:
                    bills = [edge["node"] for edge in result["bills"]["edges"]]
                    if bills:
                        print(f"Retrieved {len(bills)} bills for '{search_term}' "
                              f"from {jurisdiction}")
                        return bills

                time.sleep(RATE_LIMIT_DELAY)

        return []

    def fetch_bill_content(self, url: str) -> str:
        """Fetch and extract text content from a bill URL."""
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            return soup.get_text()

        except (requests.RequestException, Exception) as e:  # pylint: disable=broad-exception-caught
            print(f"Error fetching content from {url}: {e}")
            return ""

    def generate_compliance_alert(self, bill_title: str, bill_content: str) -> Dict:
        """Generate a compliance alert using LLMClient."""
        prompt = f"""Summarize the following legislative change for a crypto compliance officer.
Return JSON with keys: title, summary, deadline, action_required, severity.
TEXT:\n{bill_content[:MAX_TEXT_LENGTH]}"""

        try:
            response = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, Exception) as e:  # pylint: disable=broad-exception-caught
            print(f"Error generating compliance alert: {e}")
            return {
                "title": bill_title,
                "summary": "Unable to generate summary",
                "deadline": "Unknown",
                "action_required": "Review manually",
                "severity": "Unknown"
            }

    def process_bills(self) -> None:
        """Main processing pipeline for bills."""
        print(f"Using OpenStates API key: {self.openstates_key[:8]}...")
        print(f"Connecting to: {OPENSTATES_URL}")

        bills = self.fetch_bills()
        if not bills:
            print("Error: Unable to retrieve bills from OpenStates API")
            sys.exit(1)

        for bill in bills:
            if not bill.get("sources"):
                print(f"No sources found for bill: {bill.get('title', 'Unknown')}")
                continue

            url = bill["sources"][0]["url"]
            print(f"Processing bill: {bill.get('title', 'Unknown')}")

            content = self.fetch_bill_content(url)
            if not content:
                print(f"No content retrieved for bill: {bill.get('title', 'Unknown')}")
                continue

            alert = self.generate_compliance_alert(bill.get("title", "Unknown"), content)
            print(json.dumps(alert, indent=2))

            time.sleep(RATE_LIMIT_DELAY)


def main():
    """Main entry point."""
    try:
        monitor = LegislativeMonitor()
        monitor.process_bills()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
