
import os
from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from app.tools import search_codebase, get_file_dependencies, get_file_dependents, list_all_files
from app.retriever import VectorStore
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage, ToolMessage
import json
import networkx as nx

def generate_answer(query: str, vector_store: VectorStore, dependency_graph: nx.DiGraph):

    # 1. Define the tool wrapper to inject the vector_store instance
    @tool
    def search_tool(
        keywords: str,
        filter_by_file: Optional[List[str]] = None,
        filter_by_type: Optional[str] = None,
        filter_by_parent: Optional[str] = None,
    ) -> str:
        """
        Searches the codebase for functions, methods, or classes using semantic keywords and optional filters.
        
        Args:
            keywords: A string of keywords to search for, describing the desired code functionality.
            filter_by_file: A list of file paths to restrict the search to.
            filter_by_type: The type of code to search for (e.g., 'function', 'method').
            filter_by_parent: The parent class to restrict the search to (for methods).
        """
        return search_codebase(
            vector_store=vector_store,
            keywords=keywords,
            filter_by_file=filter_by_file,
            filter_by_type=filter_by_type,
            filter_by_parent=filter_by_parent
        )

    @tool
    def dependencies_tool(file_name: str) -> str:
        """
        Finds all files that the given file imports (dependencies).
        Useful for understanding what other parts of the code a specific file relies on.
        """
        return get_file_dependencies(graph=dependency_graph, file_name=file_name)

    @tool
    def dependents_tool(file_name: str) -> str:
        """
        Finds all files that import the given file (dependents).
        Useful for assessing the impact of changing a file.
        """
        return get_file_dependents(graph=dependency_graph, file_name=file_name)
    
    @tool
    def list_files_tool() -> str:
        """Lists all the source code files present in the repository."""
        return list_all_files(graph=dependency_graph)

    tools = [search_tool, dependencies_tool, dependents_tool, list_files_tool]

    # 2. Initialize the LangChain Google Generative AI model
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=os.environ.get("GOOGLE_API_KEY")
    )

    # 3. Define the system prompt
    system_prompt = """
        You are a world-class Senior Software Engineer. Your goal is to explain this codebase clearly and accurately.
        Your goal is to answer the user's question by using the provided tools to explore the codebase.
        You have two types of tools available:
        1. Code Search (`search_tool`): Use this to find specific logic, implementation details, or "how things work".
        2. Code Structure (`dependencies_tool`, `dependents_tool`, `list_files_tool`): Use these to understand the "architecture" and "impact" of changes.

        Strategy:
        - Start by using `list_files_tool` if you are unfamiliar with the project structure.
        - If a user asks about a specific feature, use `search_tool` with descriptive keywords.
        - If you find a relevant file, check its `dependencies_tool` to see what it relies on.
        
        Be exhaustive. If the first search doesn't give enough info, refine your keywords and try again.
        Once you have enough information, provide a comprehensive answer to the user.
    """


    # 4. Create the agent and executor
    agent = create_agent(
        model=llm,
        system_prompt=SystemMessage(
            content=[
                {
                    "type": "text",
                    "text": system_prompt,
                },
            ]
        ),
        tools=tools,
    )

    # 5. Execute the agent
    response = agent.invoke(
        {"messages": [HumanMessage(query)]}
    )

    # Extract final answer
    final_message = response["messages"][-1]
    answer = ""
    if isinstance(final_message.content, list) and len(final_message.content) > 0:
        answer = final_message.content[0].get("text", "")
    else:
        answer = str(final_message.content)

    # Extract tool results and intermediate thoughts for the frontend
    tool_results = []
    thoughts = []
    
    for message in response["messages"]:
        if isinstance(message, (SystemMessage, HumanMessage)):
            continue
            
        thought_entry = {"role": message.type, "content": message.content}
        
        if hasattr(message, "tool_calls") and message.tool_calls:
            thought_entry["tool_calls"] = message.tool_calls

        if isinstance(message, ToolMessage):
            try:
                # The content is a JSON string from search_codebase
                results = json.loads(message.content)
                thought_entry["content"] = results  # Store parsed JSON for cleaner frontend display
                if isinstance(results, list):
                    tool_results.extend(results)
            except (json.JSONDecodeError, TypeError):
                pass
        
        thoughts.append(thought_entry)
    
    return answer, tool_results, thoughts
