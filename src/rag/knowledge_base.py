# src/rag/knowledge_base.py
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "articles")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")


def load_articles() -> list:
    """
    Reads all .txt files from the articles folder.
    Splits them into individual sections by TITLE.
    Returns list of dicts with 'id', 'text', 'title'.
    """
    documents = []
    doc_id = 0

    articles_path = os.path.abspath(ARTICLES_DIR)
    if not os.path.exists(articles_path):
        print(f"Articles folder not found: {articles_path}")
        return []

    for filename in os.listdir(articles_path):
        if not filename.endswith(".txt"):
            continue

        filepath = os.path.join(articles_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by TITLE: marker
        sections = content.split("TITLE:")
        for section in sections:
            section = section.strip()
            if not section:
                continue

            lines = section.split("\n", 1)
            title = lines[0].strip()
            text = lines[1].strip() if len(lines) > 1 else ""

            if title and text:
                documents.append({
                    "id": f"doc_{doc_id}",
                    "title": title,
                    "text": f"{title}\n\n{text}",
                })
                doc_id += 1

    print(f"Loaded {len(documents)} documents from articles.")
    return documents


def get_knowledge_base():
    """
    Creates or loads the ChromaDB vector store.
    Uses OpenAI embeddings to index financial articles.
    Returns the ChromaDB collection.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    # Use OpenAI embeddings for best quality
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    # Create persistent ChromaDB client
    chroma_path = os.path.abspath(CHROMA_DIR)
    client = chromadb.PersistentClient(path=chroma_path)

    # Get or create collection
    collection = client.get_or_create_collection(
        name="finance_knowledge",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    # Only index if collection is empty
    if collection.count() == 0:
        print("Indexing articles into ChromaDB for the first time...")
        documents = load_articles()

        if documents:
            collection.add(
                ids=[d["id"] for d in documents],
                documents=[d["text"] for d in documents],
                metadatas=[{"title": d["title"]} for d in documents],
            )
            print(f"Successfully indexed {len(documents)} documents!")
        else:
            print("No documents found to index.")
    else:
        print(f"Knowledge base ready with {collection.count()} documents.")

    return collection


def retrieve_context(question: str, n_results: int = 3) -> str:
    """
    Searches the knowledge base for content relevant to the question.
    Returns the top matching passages as a single string.
    """
    try:
        collection = get_knowledge_base()

        results = collection.query(
            query_texts=[question],
            n_results=min(n_results, collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        # Combine top results into context string
        context_parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_parts.append(f"[{meta['title']}]\n{doc}")

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return ""