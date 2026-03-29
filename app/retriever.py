import os
import time
from typing import List
from app.embeddings import embed_texts
from pinecone import Pinecone, ServerlessSpec


class VectorStore:
    def __init__(self):
        self.api_key = os.environ.get("PINECONE_API_KEY")
        if not self.api_key:
            print("Warning: PINECONE_API_KEY not found in environment variables.")

        self.pc = Pinecone(api_key=self.api_key)
        self.index_name = "talktorepo"

    def build_index(self, documents):
        texts = [doc["content"] for doc in documents]
        if not texts:
            return
        embeddings = embed_texts(texts)
        dimension = embeddings.shape[1]

        # Check if index exists, create if not
        existing_indexes = [i.name for i in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)

        index = self.pc.Index(self.index_name)

        vectors = []
        for doc, emb in zip(documents, embeddings):
            # Truncate content to fit Pinecone metadata limits if necessary (approx 40KB)
            content_preview = doc["content"][:30000]
            
            metadata = {
                "file": doc["file"],
                "content": content_preview
            }
            if "metadata" in doc:
                metadata.update(doc["metadata"])

            vectors.append({
                "id": doc.get("id", doc["file"]),
                "values": emb.tolist(),
                "metadata": metadata
            })

        # Upsert in batches
        batch_size = 100
        for i in range(0, len(vectors), batch_size):
            index.upsert(vectors[i : i + batch_size])

    def delete_files(self, file_paths: List[str]):
        """Removes all embeddings associated with the given file paths."""
        if not file_paths:
            return
        index = self.pc.Index(self.index_name)
        for path in file_paths:
            try:
                # Delete vectors where the 'file' metadata matches the path
                index.delete(filter={"file": {"$eq": path}})
            except Exception as e:
                print(f"Error deleting embeddings for {path}: {e}")

    def search(self, query, k=5, filter=None):
        index = self.pc.Index(self.index_name)
        
        # Embed query
        query_embedding = embed_texts([query])[0].tolist()

        # Search Pinecone
        response = index.query(
            vector=query_embedding,
            top_k=k,
            include_metadata=True,
            filter=filter
        )

        results = []
        for match in response['matches']:
            if match.metadata:
                results.append(dict(match.metadata))

        return results