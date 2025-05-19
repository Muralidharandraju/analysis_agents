from crewai import Agent, Task, Process, Crew, LLM
from crewai.knowledge.source.csv_knowledge_source import CSVKnowledgeSource
from crewai.knowledge.source.excel_knowledge_source import ExcelKnowledgeSource
from crewai.knowledge.source.pdf_knowledge_source import PDFKnowledgeSource
import yaml
import os
from dotenv import load_dotenv
import json
# from crewai.knowledge.knowledge_config import KnowledgeConfig

# knowledge_config = KnowledgeConfig(results_limit=10, score_threshold=0.5)


load_dotenv()

# Load config and setup LLM
try:
    with open('config.json') as f:
        config = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("config.json not found")
except json.JSONDecodeError:
    raise json.JSONDecodeError("Invalid JSON in config.json")

llm = LLM(model=config.get("llm_model", "ollama/gemma3"),
          base_url=config.get("ollama_base_url", "http://localhost:11434"),
          temperature=config.get("llm_temperature", 0))

# CSV_FILE_PATH = "Procurement KPI Analysis Dataset.csv"

def load_agents(agents_file: str, llm: LLM, knowledge_sources: list):
    """Loads agent configurations from a YAML file."""
    agents = {}

    with open(agents_file, 'r') as f:
        agent_configs = yaml.safe_load(f)
        if agent_configs:
            for config in agent_configs:
                llm_config = config.get("llm_model_config") or {"temperature": 0}
                agent_llm = LLM(model=config.get("llm_model", llm.model),
                               base_url=config.get("llm_base_url", llm.base_url),
                               temperature=llm_config.get("temperature", 0))
                agent = Agent(
                    role=config['role'],
                    goal=config['goal'],
                    backstory=config['backstory'],
                    llm=agent_llm,
                    verbose=True,
                    allow_delegation=config.get('allow_delegation', True),
                    knowledge_source = knowledge_sources,
                )
                agents[config['name']] = agent
    return agents

def load_tasks(tasks_file: str, agents: dict):
    """Loads task configurations from a YAML file and associates them with agents."""
    tasks = {}
    task_list = []
    with open(tasks_file, 'r') as f:
        task_configs = yaml.safe_load(f)
        if task_configs:
            for config in task_configs:
                agent_name = config.get('agent_name')
                if agent_name and agent_name in agents:
                    task = Task(
                        description=config['description'],
                        expected_output=config['expected_output'],
                        agent=agents[agent_name],
                        context=[tasks[config['context_task']]] if config.get('context_task') and config['context_task'] in tasks else []
                    )
                    tasks[config['name']] = task
                    task_list.append(task)
                else:
                    raise ValueError(f"Agent '{agent_name}' not found for task '{config['name']}'")
    return task_list


def load_knowledge(knowledge_folder: str):
    """Loads knowledge sources based on files in the knowledge folder."""
    knowledge = []
    # csv_files = [os.path.join(knowledge_folder, f) for f in os.listdir(knowledge_folder) if f.endswith(".csv")]
    # pdf_files = [os.path.join(knowledge_folder, f) for f in os.listdir(knowledge_folder) if f.endswith(".pdf")]
    # excel_files = [os.path.join(knowledge_folder, f) for f in os.listdir(knowledge_folder) if f.endswith(".xlsx")]

    # if csv_files:
    knowledge.append(CSVKnowledgeSource(file_paths=knowledge_folder)) 

    # if pdf_files:
    #     knowledge.append(PDFKnowledgeSource(file_paths=pdf_files)) 

    # if excel_files:
    #     knowledge.append(ExcelKnowledgeSource(file_paths=excel_files))
    if not knowledge:
        raise ValueError("No valid knowledge sources found in the specified folder.")

    return knowledge

def create_data_analysis_crew(knowledge_folder: str):
    """Creates the data analysis crew with dynamic knowledge sources."""
    agents_file =  config['agent_name']
    tasks_file = config['task_name']
    knowledge_sources = load_knowledge(knowledge_folder)
    agents = load_agents(agents_file, llm, knowledge_sources)
    tasks = load_tasks(tasks_file, agents)

    data_analysis_crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True
    )
    return data_analysis_crew

