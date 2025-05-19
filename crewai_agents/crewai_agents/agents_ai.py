from crewai import Agent, Task, Process, Crew,LLM
from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
import sys
sys.path.append("..") # Make sure this path is correct for your project structure
from dotenv import load_dotenv
import json


# Assuming excel_tool is defined as above

load_dotenv()

# Load config and setup LLM (as in your original code)
with open('config.json') as f:
    config = json.load(f)


llm = LLM(model="ollama/gemma3", base_url="http://localhost:11434",temperature=0)


csv_file_path = "Procurement KPI Analysis Dataset.csv"


# Create CSV knowledge source (if you still need direct CSV querying)
csv_source = CSVKnowledgeSource(file_paths=[csv_file_path])

# --- Agent Definitions ---

# Agent 1: Data Retriever
data_retriever_agent = Agent(
    role="Data Retriever Specialist",
    goal="Retrieve specific data points or summaries from data files (CSV: ", 
    backstory=(
        "You are an expert at navigating and extracting information from structured data files like CSV and Excel. "
        "You receive a query and precisely locate and return the requested data subset, ensuring accuracy. "
        f"You have access to a CSV file."
        "Use the 'Excel Data Reader' tool for the Excel file."
    ),
    
    knowledge_source=[csv_source], # Keep CSV source if needed for direct querying
    llm=llm,
    verbose=True,
    allow_delegation=False # This agent shouldn't delegate, it executes retrieval tasks
)

# Agent 2: Data Analyst
data_analyst_agent = Agent(
    role="Senior Data Analyst",
    goal="Analyze the provided data subsets, identify trends, patterns, and key insights. Verify findings and structure the analysis clearly.",
    backstory=(
        "You are a meticulous data analyst. You receive raw data extracts relevant to a query. "
        "Your job is to perform calculations, comparisons, and statistical analysis to uncover meaningful insights. "
        "If the provided data seems insufficient or ambiguous, you can delegate back to the 'Data Retriever Specialist' to request more specific data or clarification."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=True # Allows asking the retriever for more info
    # This agent doesn't directly need tools/knowledge sources if it relies on Agent 1's output
)

# Agent 3: Report Writer
report_writer_agent = Agent(
    role="Technical Report Writer",
    goal="Compile the findings and analysis into a clear, concise, and well-structured report in Markdown format.",
    backstory=(
        "You are skilled at communicating complex analytical results in an easy-to-understand format. "
        "You take the structured analysis provided by the Data Analyst and transform it into a polished final report, ensuring clarity and accuracy."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# --- Task Definitions ---

# Task 1: Retrieve Data
# We also pass the original user question.
retrieval_task = Task(
    description=(
        "User query: '{question}'. "
        "Retrieve the necessary data from the available sources"
        "For CSV data, query the knowledge source."
    ),
    expected_output="A text block containing the raw data snippets, summaries, or relevant information extracted from the file(s) needed to answer the user's query.",
    agent=data_retriever_agent,
    # You might pass file paths as context if needed, e.g., context=[{"csv_path": csv_file_path, "excel_path": excel_file_path}]
    # However, embedding in description/backstory is often sufficient.
)

# Task 2: Analyze Data
analysis_task = Task(
    description=(
        "Analyze the data provided in the context (output of the retrieval task) to address the original user query: '{question}'. "
        "Perform calculations, identify key trends, patterns, highs, lows, or other relevant insights based *only* on the provided data. "
        "Structure your findings clearly. If the data is insufficient, state what's missing or request clarification (delegation)."
    ),
    expected_output="A structured analysis report containing key findings, calculations, and insights derived *solely* from the input data. Clearly state any limitations.",
    agent=data_analyst_agent,
    context=[retrieval_task] # Pass the output of the first task
)

# Task 3: Write Report
writing_task = Task(
    description=(
        "Compile the structured analysis provided in the context into a final, well-formatted report in Markdown. "
        "Ensure the report directly answers the original user query: '{question}' based on the analysis. "
        "The report should be clear, concise, and easy to read."
    ),
    expected_output="A final, polished report in Markdown format summarizing the analysis and answering the user query.",
    agent=report_writer_agent,
    context=[analysis_task] # Pass the output of the second task
)

# --- Crew Definition ---
data_analysis_crew = Crew(
    agents=[data_retriever_agent, data_analyst_agent, report_writer_agent],
    tasks=[retrieval_task, analysis_task, writing_task],
    process=Process.sequential, # Tasks run one after another
    verbose=True
)

# --- Kickoff ---

user_query = "I have provided the Procurement data and want to know the key driving factors based on the item category in provided data and order status is delivered"


result = data_analysis_crew.kickoff(inputs={"question": user_query})

print("\n\n--- Final Report ---")
print(result)
