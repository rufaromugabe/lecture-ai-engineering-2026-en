"""Lecture 03 homework (Advanced a): the exercise agent rebuilt with Google ADK.

Same INSTRUCTIONS and the same tool functions as app/agent.py; only the agent-building part differs.
Run from the repo root:
    PYTHONPATH=. uv run --with google-adk adk run adk_agent/glossary_agent
"""

from google.adk.agents import Agent

from app import tools
from app.agent import INSTRUCTIONS

root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="glossary_agent",
    instruction=INSTRUCTIONS,
    tools=[tools.search_glossary, tools.get_lecture_summary, tools.make_quiz],  # tools used in the exercise
)
