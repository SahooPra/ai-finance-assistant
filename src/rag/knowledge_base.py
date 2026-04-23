# src/rag/knowledge_base.py
import os
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

ARTICLES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "articles")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")


def parse_article_metadata(content: str, filename: str) -> dict:
    """
    Extracts TITLE, SOURCE, and URL from article text.
    Falls back to filename if markers not found.
    """
    lines = content.split("\n")
    title = filename.replace(".txt", "").replace("_", " ")
    source = "Finnie Knowledge Base"
    url = ""

    for line in lines[:10]:
        line = line.strip()
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("SOURCE:"):
            source = line.replace("SOURCE:", "").strip()
        elif line.startswith("URL:"):
            url = line.replace("URL:", "").strip()

    return {"title": title, "source": source, "url": url}


def load_articles() -> list:
    """
    Reads all .txt files from the articles folder.
    Splits them by TITLE marker into individual sections.
    Returns list of dicts with id, text, and metadata.
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

        # Check if file uses TITLE: markers (multi-section file)
        if content.count("TITLE:") > 1:
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
                        "text": f"TITLE: {title}\n\n{text}",
                        "metadata": {
                            "title": title,
                            "source": "Finnie Knowledge Base",
                            "url": "",
                            "filename": filename,
                        }
                    })
                    doc_id += 1
        else:
            # Single article file (Wikipedia format)
            meta = parse_article_metadata(content, filename)

            # Split into chunks of ~1000 chars for better retrieval
            chunks = chunk_text(content, chunk_size=1000, overlap=100)
            for i, chunk in enumerate(chunks):
                documents.append({
                    "id": f"doc_{doc_id}",
                    "text": chunk,
                    "metadata": {
                        "title": meta["title"],
                        "source": meta["source"],
                        "url": meta["url"],
                        "filename": filename,
                        "chunk": i,
                    }
                })
                doc_id += 1

    print(f"Loaded {len(documents)} document chunks from articles.")
    return documents


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list:
    """
    Splits long text into overlapping chunks for better RAG retrieval.
    Overlap ensures context isn't lost at chunk boundaries.
    """
    words = text.split()
    chunks = []
    start = 0
    words_per_chunk = chunk_size // 6  # rough estimate

    while start < len(words):
        end = start + words_per_chunk
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - (overlap // 6)

    return chunks


def get_knowledge_base():
    """
    Creates or loads the ChromaDB vector store.
    Forces re-index if new articles have been added.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    chroma_path = os.path.abspath(CHROMA_DIR)
    client = chromadb.PersistentClient(path=chroma_path)

    collection = client.get_or_create_collection(
        name="finance_knowledge",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    if collection.count() == 0:
        print("Indexing articles into ChromaDB for the first time...")
        documents = load_articles()

        if documents:
            collection.add(
                ids=[d["id"] for d in documents],
                documents=[d["text"] for d in documents],
                metadatas=[d["metadata"] for d in documents],
            )
            print(f"Successfully indexed {len(documents)} document chunks!")
    else:
        print(f"Knowledge base ready with {collection.count()} chunks.")

    return collection


def retrieve_context(question: str, n_results: int = 3) -> tuple:
    """
    Searches the knowledge base for relevant content.
    Returns (context_text, citations_list) tuple.
    citations_list contains source metadata for each result.
    """
    try:
        collection = get_knowledge_base()

        results = collection.query(
            query_texts=[question],
            n_results=min(n_results, collection.count()),
        )

        if not results["documents"] or not results["documents"][0]:
            return "", []

        context_parts = []
        citations = []

        for doc, meta in zip(
            results["documents"][0],
            results["metadatas"][0]
        ):
            title = meta.get("title", "Unknown")
            source = meta.get("source", "Finnie Knowledge Base")
            url = meta.get("url", "")

            context_parts.append(f"[{title}]\n{doc}")

            # Build citation entry
            citation = {"title": title, "source": source}
            if url:
                citation["url"] = url

            # Avoid duplicate citations
            if citation not in citations:
                citations.append(citation)

        context_text = "\n\n---\n\n".join(context_parts)
        return context_text, citations

    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return "", []


def rebuild_knowledge_base():
    """
    Deletes and rebuilds the ChromaDB collection from scratch.
    Run this after adding new articles.
    """
    api_key = os.getenv("OPENAI_API_KEY")

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small"
    )

    chroma_path = os.path.abspath(CHROMA_DIR)
    client = chromadb.PersistentClient(path=chroma_path)

    # Delete existing collection
    try:
        client.delete_collection("finance_knowledge")
        print("Deleted old knowledge base.")
    except Exception:
        pass

    # Recreate
    collection = client.get_or_create_collection(
        name="finance_knowledge",
        embedding_function=openai_ef,
        metadata={"hnsw:space": "cosine"}
    )

    documents = load_articles()
    if documents:
        collection.add(
            ids=[d["id"] for d in documents],
            documents=[d["text"] for d in documents],
            metadatas=[d["metadata"] for d in documents],
        )
        print(f"Rebuilt knowledge base with {len(documents)} chunks!")

    return collection