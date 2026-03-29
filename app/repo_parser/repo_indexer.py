
import os
import json
import hashlib

from .parser import CodeParser
from .graph_builder import DependencyGraph


class RepoIndexer:

    def __init__(self, repo_path):

        self.repo_path = repo_path
        self.parser = CodeParser()
        self.graph = DependencyGraph()

        self.repo_structure = {}
        self.cache_path = os.path.join(self.repo_path, ".talktorepo.cache")
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_path, "w") as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Failed to save cache: {e}")

    def index(self):
        documents = []
        visited_files = set()
        for root, dirs, files in os.walk(self.repo_path):
            # Skip hidden directories like .git
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            for file in files:
                file_path = os.path.join(root, file)
                relative = os.path.relpath(file_path, self.repo_path)

                if file.endswith((".py", ".js", ".ts", ".java", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".go", ".rs")): # Handle Code files with parsing
                    visited_files.add(relative)

                    # Check if file is unchanged via hash
                    # We peek at the hash before full parsing
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_hash = hashlib.sha256(f.read().encode("utf-8")).hexdigest()

                    if relative in self.cache and self.cache[relative].get("hash") == source_hash:
                        # Reconstruct state from cache, skip parsing and embedding
                        cached_data = self.cache[relative]["data"]
                        self.repo_structure[relative] = cached_data
                        self.graph.add_file(relative)
                        self.graph.add_imports(relative, cached_data["imports"])
                        continue

                    parsed = self.parser.parse_file(file_path)
                    self.repo_structure[relative] = {
                        "functions": parsed["functions"],
                        "classes": parsed["classes"],
                        "imports": parsed["imports"]
                    }

                    self.graph.add_file(relative)
                    self.graph.add_imports(relative, parsed["imports"])

                    # Update cache entry
                    self.cache[relative] = {
                        "hash": parsed["hash"],
                        "data": self.repo_structure[relative]
                    }

                    # Create hierarchical documents for embedding
                    for cls in parsed["classes"]:
                        # 1. Index the class itself
                        documents.append({
                            "id": f"{relative}::{cls['name']}",
                            "content": cls["text"],
                            "file": relative,
                            "metadata": {
                                "type": "class",
                                "name": cls["name"]
                            }
                        })
                        
                        # 2. Methods (if extracted, e.g. Python)
                        for method in cls.get("methods", []):
                            documents.append({
                                "id": f"{relative}::{cls['name']}::{method['name']}",
                                "content": method["text"],
                                "file": relative,
                                "metadata": {
                                    "type": "method",
                                    "name": method["name"],
                                    "parent": cls["name"]
                                }
                            })

                    # 3. Functions
                    for func in parsed["functions"]:
                        documents.append({
                            "id": f"{relative}::{func['name']}",
                            "content": func["text"],
                            "file": relative,
                            "metadata": {
                                "type": "function",
                                "name": func["name"]
                            }
                        })
                
                elif file.lower().endswith(".md"): # Handle Markdown files
                    visited_files.add(relative)

                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        documents.append({
                            "id": relative,
                            "content": content,
                            "file": relative,
                            "metadata": {
                                "type": "documentation"
                            }
                        })
                        # Add the file to the dependency graph so it can be listed
                        self.graph.add_file(relative)
                        # Add to cache for deletion tracking
                        self.cache[relative] = {"hash": hashlib.sha256(content.encode()).hexdigest(), "data": {}}
                    except Exception as e:
                        print(f"Error reading or processing markdown file {file_path}: {e}")

                # Register other common file types in the graph so the LLM knows they exist
                elif file.endswith((".html", ".css", ".json", ".yml", ".yaml", ".txt", ".xml")):
                    visited_files.add(relative)
                    
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        documents.append({
                            "id": relative,
                            "content": content,
                            "file": relative,
                            "metadata": {
                                "type": "code_file"
                            }
                        })
                        # Add to cache for deletion tracking
                        self.cache[relative] = {"hash": hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest(), "data": {}}
                    except Exception as e:
                        print(f"Error reading file {file_path}: {e}")

                    self.graph.add_file(relative)

        # Identify and remove files from cache that were not visited (deleted from disk)
        deleted_files = [f for f in self.cache.keys() if f not in visited_files]
        for f in deleted_files:
            del self.cache[f]

        self._save_cache()
        return documents, deleted_files


    def get_graph(self):

        return self.graph.get_graph()