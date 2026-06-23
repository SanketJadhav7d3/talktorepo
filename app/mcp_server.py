"""
TalkToRepo MCP server (stdio transport).

Exposes the repository-intelligence capabilities of TalkToRepo as MCP tools so
that an MCP host (Claude Desktop / Claude Code) can act as the agent itself,
replacing the bundled Gemini/LangChain agent in `app/llm.py`.

Run locally:
    uv run python -m app.mcp_server

Register in an MCP host config (e.g. Claude Desktop / Claude Code) with:
    command: <path-to>/.venv/Scripts/python.exe
    args:    ["-m", "app.mcp_server"]
    cwd:     <path-to>/talktorepo
    env:     { "PINECONE_API_KEY": "...", "GOOGLE_API_KEY": "..." }

Note: GOOGLE_API_KEY is NOT required for the MCP server itself (Claude is the
agent now); only PINECONE_API_KEY is needed for vector search.
"""

import os
import json
import pickle
from typing import List, Optional

import networkx as nx
from mcp.server.fastmcp import FastMCP

from app.ingest import clone_repo
from app.retriever import VectorStore
from app.repo_parser.repo_indexer import RepoIndexer
from app import tools as repo_tools

# --- Persistent state -------------------------------------------------------
# Unlike the FastAPI app, an MCP stdio server may be started/stopped per
# session. Pinecone vectors persist on their own, but the NetworkX dependency
# graph does not, so we persist it to disk and reload it on startup.

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".mcp_state")
GRAPH_PATH = os.path.join(STATE_DIR, "dependency_graph.pkl")


class AppState:
    def __init__(self):
        self.vector_store: Optional[VectorStore] = None
        self.dependency_graph: nx.DiGraph = self._load_graph()

    def _load_graph(self) -> nx.DiGraph:
        if os.path.exists(GRAPH_PATH):
            try:
                with open(GRAPH_PATH, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Failed to load saved graph: {e}")
        return nx.DiGraph()

    def save_graph(self):
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(GRAPH_PATH, "wb") as f:
            pickle.dump(self.dependency_graph, f)

    def get_vector_store(self) -> VectorStore:
        if self.vector_store is None:
            self.vector_store = VectorStore()
        return self.vector_store


state = AppState()

mcp = FastMCP("talktorepo")


# --- Tools ------------------------------------------------------------------

@mcp.tool()
def index_repo(repo_url: str) -> str:
    """Clone a GitHub repository and index it for searching.

    Parses the code with AST/Tree-sitter, builds a dependency graph, and stores
    embeddings in the vector store. Run this once before using the other tools.

    Args:
        repo_url: The HTTPS URL of the GitHub repository to index.
    """
    repo_path = clone_repo(repo_url)
    indexer = RepoIndexer(repo_path)
    documents, deleted_files = indexer.index()

    state.dependency_graph = indexer.get_graph()
    state.save_graph()

    vs = state.get_vector_store()
    vs.delete_files(deleted_files)
    vs.build_index(documents)

    return json.dumps({
        "message": "Repository indexed successfully",
        "files_indexed": state.dependency_graph.number_of_nodes(),
        "documents_embedded": len(documents),
        "files_removed": len(deleted_files),
    })


@mcp.tool()
def search_codebase(
    keywords: str,
    filter_by_file: Optional[List[str]] = None,
    filter_by_type: Optional[str] = None,
    filter_by_parent: Optional[str] = None,
) -> str:
    """Semantically search the indexed codebase for functions, methods, or classes.

    Args:
        keywords: Keywords describing the desired code functionality.
        filter_by_file: Optional list of file paths to restrict the search to.
        filter_by_type: Optional code type, e.g. 'function', 'method', 'class'.
        filter_by_parent: Optional parent class name (for methods).
    """
    if state.dependency_graph.number_of_nodes() == 0:
        return json.dumps({"error": "No repository indexed yet. Call index_repo first."})

    return repo_tools.search_codebase(
        vector_store=state.get_vector_store(),
        keywords=keywords,
        filter_by_file=filter_by_file,
        filter_by_type=filter_by_type,
        filter_by_parent=filter_by_parent,
    )


@mcp.tool()
def get_file_dependencies(file_name: str) -> str:
    """List the files that the given file imports (its dependencies).

    Args:
        file_name: The repository-relative path of the file to inspect.
    """
    return repo_tools.get_file_dependencies(state.dependency_graph, file_name)


@mcp.tool()
def get_file_dependents(file_name: str) -> str:
    """List the files that import the given file (its dependents).

    Useful for assessing the impact of changing a file.

    Args:
        file_name: The repository-relative path of the file to inspect.
    """
    return repo_tools.get_file_dependents(state.dependency_graph, file_name)


@mcp.tool()
def list_all_files() -> str:
    """List all source code files present in the indexed repository."""
    return repo_tools.list_all_files(state.dependency_graph)


if __name__ == "__main__":
    mcp.run()
