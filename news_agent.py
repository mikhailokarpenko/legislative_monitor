"""News Agent module for processing and summarizing news articles.

This module provides a Streamlit web interface for searching, synthesizing,
and summarizing news articles using AI agents.
"""

import os
from datetime import datetime
from typing import Tuple

import streamlit as st
from dotenv import load_dotenv
from duckduckgo_search import DDGS
from swarm import Swarm, Agent

from llm_client import LLMClient

# Configuration constants
load_dotenv()
BASE_URL = os.getenv("OPENAI_BASE_URL")
API_KEY = os.getenv("OPENAI_API_KEY")
MAX_NEWS_RESULTS = 3

# Initialize clients
llm = LLMClient()
model = llm.get_model()
openai_client = llm.get_client()
client = Swarm(client=openai_client)

st.set_page_config(page_title="AI News Processor", page_icon="📰")
st.title("📰 News Inshorts Agent")

def search_news(topic: str) -> str:
    """Search for news articles using DuckDuckGo.
    
    Args:
        topic (str): The news topic to search for
        
    Returns:
        str: Formatted news results or error message
    """
    try:
        with DDGS() as search_engine:
            results = search_engine.text(
                f"{topic} news {datetime.now().strftime('%Y-%m')}",
                max_results=MAX_NEWS_RESULTS
            )
            if results:
                news_results = "\n\n".join([
                    f"Title: {result['title']}\n"
                    f"URL: {result['href']}\n"
                    f"Summary: {result['body']}"
                    for result in results
                ])
                return news_results
            return f"No news found for {topic}."
    except (ConnectionError, TimeoutError, ValueError) as e:
        return f"Error searching for news: {str(e)}"

# Create specialized agents
search_agent = Agent(
    name="News Searcher",
    instructions="""
    You are a news search specialist. Your task is to:
    1. Search for the most relevant and recent news on the given topic
    2. Ensure the results are from reputable sources
    3. Return the raw search results in a structured format
    """,
    functions=[search_news],
    model=model
)

synthesis_agent = Agent(
    name="News Synthesizer",
    instructions="""
    You are a news synthesis expert. Your task is to:
    1. Analyze the raw news articles provided
    2. Identify the key themes and important information
    3. Combine information from multiple sources
    4. Create a comprehensive but concise synthesis
    5. Focus on facts and maintain journalistic objectivity
    6. Write in a clear, professional style
    Provide a 2-3 paragraph synthesis of the main points.
    """,
    model=model
)

summary_agent = Agent(
    name="News Summarizer",
    instructions="""
    You are an expert news summarizer combining AP and Reuters style clarity with digital-age brevity.

    Your task:
    1. Core Information:
       - Lead with the most newsworthy development
       - Include key stakeholders and their actions
       - Add critical numbers/data if relevant
       - Explain why this matters now
       - Mention immediate implications

    2. Style Guidelines:
       - Use strong, active verbs
       - Be specific, not general
       - Maintain journalistic objectivity
       - Make every word count
       - Explain technical terms if necessary

    Format: Create a single paragraph of 250-400 words that informs and engages.
    Pattern: [Major News] + [Key Details/Data] + [Why It Matters/What's Next]

    Focus on answering: What happened? Why is it significant? What's the impact?

    IMPORTANT: Provide ONLY the summary paragraph. Do not include any introductory phrases, 
    labels, or meta-text like "Here's a summary" or "In AP/Reuters style."
    Start directly with the news content.
    """,
    model=model
)

def process_news(topic: str) -> Tuple[str, str, str]:
    """Run the complete news processing workflow.
    
    Args:
        topic (str): The news topic to process
        
    Returns:
        Tuple[str, str, str]: (raw_news, synthesized_news, final_summary)
    """
    with st.status("Processing news...", expanded=True) as status:
        # Search
        status.write("🔍 Searching for news...")
        search_response = client.run(
            agent=search_agent,
            messages=[{"role": "user", "content": f"Find recent news about {topic}"}]
        )
        raw_news = search_response.messages[-1]["content"]
        # Synthesize
        status.write("🔄 Synthesizing information...")
        synthesis_response = client.run(
            agent=synthesis_agent,
            messages=[{"role": "user", "content": f"Synthesize these news articles:\n{raw_news}"}]
        )
        synthesized_news = synthesis_response.messages[-1]["content"]
        # Summarize
        status.write("📝 Creating summary...")
        summary_response = client.run(
            agent=summary_agent,
            messages=[{"role": "user", "content": f"Summarize this synthesis:\n{synthesized_news}"}]
        )
        return raw_news, synthesized_news, summary_response.messages[-1]["content"]

# User Interface
topic = st.text_input("Enter news topic:", value="artificial intelligence")
if st.button("Process News", type="primary"):
    if topic:
        try:
            raw_news, synthesized_news, final_summary = process_news(topic)
            st.header(f"📝 News Summary: {topic}")
            st.markdown(final_summary)
        except (ConnectionError, TimeoutError) as e:
            st.error(f"Network error occurred: {str(e)}")
        except ValueError as e:
            st.error(f"Invalid input: {str(e)}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            st.error(f"An unexpected error occurred: {str(e)}")
    else:
        st.error("Please enter a topic!")
