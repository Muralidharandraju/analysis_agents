from crewai import Agent, Task, Process,LLM,Crew
from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
import sys
sys.path.append("..")
from dotenv import load_dotenv

import json

load_dotenv()


with open('config.json') as f:
    config = json.load(f)

model_name = config['model_name']

# Create a CSV knowledge source
csv_source = CSVKnowledgeSource(
    file_paths=["Historical Product Demand.csv"]
)

# Create an LLM with a temperature of 0 to ensure deterministic outputs
# llm = LLM(model=model_name, temperature=0)

llm = LLM(model="ollama/gemma3", base_url="http://localhost:11434",temperature=0.1)

analysis_agent = Agent(
    role="Senior Data Analyst",
    goal="You know everything about the product demand.",
    backstory="You are a senior data analyst with expertise in data analysis and visualization. You are capable of analyzing complex datasets and generating insights."
    "you will be provided with a CSV file containing historical product demand data. Your task is to analyze the data and provide insights on product demand trends, seasonality, and any other relevant patterns."
    "You will also be able to answer questions related to the data and provide recommendations based on your analysis.",
    knowledge_source=[csv_source],
    llm=llm,
)   

research_analyst = Agent(
        role="Research Analyst",
        goal="Analyze and synthesize raw information into structured insights.",
        backstory="An expert at analyzing information, identifying patterns, and extracting key insights. If required, can delagate the task of fact checking/verification to only. Passes the final results to the 'Technical Writer' only.",
        verbose=True,
        allow_delegation=True,
        llm=llm,
    )


# Define the technical writer
technical_writer = Agent(
        role="Technical Writer",
        goal="Create well-structured, clear, and comprehensive responses in markdown format, with citations/source links (urls).",
        backstory="An expert at communicating complex information in an accessible way.",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

# Create a task for the agent
knowledge_task = Task(
    description="Answer the following questions about the user: {question}",
    expected_output="Detailed raw search results including sources.",
    agent=research_analyst,
    context=[csv_source],
)

analysis_task = Task(
        description="Analyze the raw search results, identify key information, verify facts and prepare a structured analysis.",
        agent=research_analyst,
        expected_output="A structured analysis of the information with verified facts and key insights, along with source links",
        context=[research_analyst]
    )

writing_task = Task(
        description="Create a comprehensive, well-organized response based on the research analysis.",
        agent=technical_writer,
        expected_output="A clear, comprehensive response that directly answers the query with proper citations/source links (urls).",
        context=[analysis_task]
    )


crew = Crew(
    agents=[analysis_agent,research_analyst,technical_writer],
    tasks=[knowledge_task, analysis_task, writing_task],
    verbose=True,
    process=Process.sequential,
    knowledge_sources=[csv_source], # Enable knowledge by adding the sources here. You can also add more sources to the sources list.
)

result = crew.kickoff(inputs={"question": "identify the products which the highest and lowest sales "})
print(result)