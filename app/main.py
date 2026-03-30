
from fastapi import FastAPI
from pydantic import BaseModel
import networkx as nx


from app.ingest import clone_repo
from app.retriever import VectorStore
from app.llm import generate_answer
from app.repo_parser.repo_indexer import RepoIndexer



app = FastAPI()

class AppState:
    def __init__(self):
        self.vector_store = VectorStore()
        self.dependency_graph = nx.DiGraph()

state = AppState()

class RepoRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str


@app.get("/")
def home():
    return "Home"


@app.post("/index_repo")
def index_repo(request: RepoRequest):

    repo_path = clone_repo(request.repo_url)

    indexer = RepoIndexer(repo_path)

    documents, deleted_files = indexer.index()
    
    state.dependency_graph = indexer.get_graph()

    # Remove embeddings for files that no longer exist
    state.vector_store.delete_files(deleted_files)

    state.vector_store.build_index(documents)

    return {"message": "Repository indexed successfully"}

@app.get("/graph")
def get_graph():
    """Returns the nodes and edges of the dependency graph for visualization."""
    def get_color(node_name):
        if node_name.endswith('.py'): return "#3776AB"  # Python Blue
        if node_name.endswith(('.js', '.ts')): return "#F7DF1E" # JS Yellow
        if node_name.endswith('.md'): return "#083FA1" # MD Blue
        return "#94A3B8" # Default Slate

    nodes = [
        {"id": n, "label": n, "color": get_color(n)} 
        for n in state.dependency_graph.nodes()
    ]
    edges = [{"source": u, "target": v} for u, v in state.dependency_graph.edges()]
    return {"nodes": nodes, "edges": edges}

@app.post("/query")
def query_repo(request: QueryRequest):

    if state.dependency_graph.number_of_nodes() == 0:
        return {
            "answer": "The repository index is empty. This usually happens if the backend server restarted. Please click 'Index Repository' again to reload the graph.",
            "results": []
        }

    # The new generate_answer is an agent that will perform searches itself.
    answer, results, thoughts = generate_answer(request.query, state.vector_store, state.dependency_graph)

    return {
        "answer": answer, 
        "results": results,
        "thoughts": thoughts
    }
