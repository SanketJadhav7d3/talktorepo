from app.retriever import VectorStore
from typing import Optional, List
import json
import networkx as nx

def search_codebase(
    vector_store: VectorStore,
    keywords: str,
    filter_by_file: Optional[List[str]] = None,
    filter_by_type: Optional[str] = None,
    filter_by_parent: Optional[str] = None,
) -> str:
    """
    Searches the codebase for functions, methods, or classes using semantic keywords and optional filters.
    
    Args:
        vector_store: The VectorStore instance to use for searching.
        keywords: A string of keywords to search for, describing the desired code functionality.
        filter_by_file: A list of file paths to restrict the search to.
        filter_by_type: The type of code to search for (e.g., 'function', 'method').
        filter_by_parent: The parent class to restrict the search to (for methods).

    Returns:
        A JSON string of the search results.
    """
    pinecone_filter = {}
    if filter_by_file:
        pinecone_filter['file'] = {'$in': filter_by_file}
    if filter_by_type:
        pinecone_filter['type'] = filter_by_type
    if filter_by_parent:
        pinecone_filter['parent'] = filter_by_parent
        
    results = vector_store.search(query=keywords, filter=pinecone_filter if pinecone_filter else None)
    
    return json.dumps(results)


def get_file_dependencies(graph: nx.DiGraph, file_name: str) -> str:
    """
    Finds all files that the given file imports (dependencies).
    Args:
        graph: The dependency graph.
        file_name: The name of the file to find dependencies for.
    Returns:
        A JSON string list of files that file_name depends on.
    """
    if file_name not in graph:
        return json.dumps({"error": f"File '{file_name}' not found in the graph."})
    
    dependencies = list(graph.successors(file_name))
    return json.dumps(dependencies)

def get_file_dependents(graph: nx.DiGraph, file_name: str) -> str:
    """
    Finds all files that import the given file (dependents).
    Args:
        graph: The dependency graph.
        file_name: The name of the file to find dependents for.
    Returns:
        A JSON string list of files that depend on file_name.
    """
    if file_name not in graph:
        return json.dumps({"error": f"File '{file_name}' not found in the graph."})
        
    dependents = list(graph.predecessors(file_name))
    return json.dumps(dependents)

def list_all_files(graph: nx.DiGraph) -> str:
    """
    Lists all the files present in the dependency graph.
    Args:
        graph: The dependency graph.
    Returns:
        A JSON string list of all file names.
    """
    files = [node for node, data in graph.nodes(data=True) if data.get('type') == 'file']
    return json.dumps(files)