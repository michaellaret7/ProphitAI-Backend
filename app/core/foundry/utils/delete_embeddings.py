from app.core.foundry.embeddings.pinecone_manager import PineconeManager
from dotenv import load_dotenv
import os

load_dotenv()

class DeleteEmbeddings:
    def __init__(self):
        self.pm = PineconeManager()
        self.pm.connect_index(
            name=os.getenv("PINECONE_INDEX_NAME"),
            host=os.getenv("PINECONE_HOST"),
        )
    
    def get_all_ids(self, namespace: str):
        return self.pm.list_vectors(namespace=namespace)

    def delete_all(self, namespace: str):
        return self.pm.delete(delete_all=True, namespace=namespace)

    def delete_by_id(self, ids: list[str], namespace: str):
        return self.pm.delete(ids=ids, namespace=namespace)


if __name__ == "__main__":
    de = DeleteEmbeddings()
    de.delete_all(namespace="earnings_calls")