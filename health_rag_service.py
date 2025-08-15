import os
from haystack import Pipeline, Document
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import OpenAIDocumentEmbedder, \
    OpenAITextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.components.retrievers import InMemoryEmbeddingRetriever
from haystack.document_stores.in_memory import InMemoryDocumentStore
from typing import List, Optional, Tuple

from dotenv_loader import api_key

os.environ["OPENAI_API_KEY"] = api_key


class HealthRAGService:
    """
    Service for handling RAG operations on health documents.
    Keeps RAG logic separate from the chatbot.
    """

    def __init__(self):
        self.document_store = None
        self.rag_pipeline = None
        self.is_initialized = False
        self.relevance_threshold = 0.5  # Minimum similarity score for
        # relevance

    def initialize(self, pdf_folder: str = "health_pdfs"):
        """Initialize the RAG system by loading and indexing PDFs"""
        print("Initializing Health RAG Service...")

        # 1. Initialize document store
        self.document_store = InMemoryDocumentStore()

        # 2. Create indexing pipeline
        indexing_pipeline = Pipeline()
        indexing_pipeline.add_component("converter", PyPDFToDocument())
        indexing_pipeline.add_component("cleaner", DocumentCleaner())
        indexing_pipeline.add_component("splitter", DocumentSplitter(
            split_by="sentence", split_length=3))
        indexing_pipeline.add_component("embedder", OpenAIDocumentEmbedder())
        indexing_pipeline.add_component("writer", DocumentWriter(
            document_store=self.document_store))

        # Connect indexing components
        indexing_pipeline.connect("converter", "cleaner")
        indexing_pipeline.connect("cleaner", "splitter")
        indexing_pipeline.connect("splitter", "embedder")
        indexing_pipeline.connect("embedder", "writer")

        # 3. Load PDFs
        if not os.path.exists(pdf_folder):
            print(
                f"PDF folder '{pdf_folder}' not found. Creating sample "
                f"PDFs...")
            from health_pdf_creator import create_health_pdfs
            create_health_pdfs()

        pdf_files = [f"{pdf_folder}/{f}" for f in os.listdir(pdf_folder)
                     if f.endswith('.pdf')]

        if not pdf_files:
            print(f"No PDF files found in {pdf_folder}")
            return False

        print(f"Loading {len(pdf_files)} PDFs...")
        indexing_pipeline.run({"converter": {"sources": pdf_files}})
        print(
            f"Indexed {self.document_store.count_documents()} document chunks")

        # 4. Create RAG pipeline
        self.rag_pipeline = Pipeline()
        self.rag_pipeline.add_component("text_embedder", OpenAITextEmbedder())
        self.rag_pipeline.add_component("retriever",
                                        InMemoryEmbeddingRetriever(
                                            document_store=self.document_store,
                                            top_k=5))

        # Connect RAG components
        self.rag_pipeline.connect("text_embedder.embedding",
                                  "retriever.query_embedding")

        self.is_initialized = True
        print("Health RAG Service initialized successfully!")
        return True

    def search_documents(self, query: str) -> Tuple[
        bool, List[Document], List[float]]:
        """
        Search for relevant documents based on query.
        Returns: (is_relevant, documents, scores)
        """
        if not self.is_initialized:
            print("RAG Service not initialized!")
            return False, [], []

        try:
            # Run retrieval
            result = self.rag_pipeline.run({
                "text_embedder": {"text": query}
            })

            documents = result["retriever"]["documents"]
            scores = [doc.score for doc in documents if hasattr(doc, 'score')]

            # Check if any documents meet relevance threshold
            is_relevant = any(score >= self.relevance_threshold for score in
                              scores) if scores else False

            if not is_relevant:
                print(
                    f"No relevant documents found (max score: "
                    f"{max(scores) if scores else 'N/A'})")

            return is_relevant, documents, scores

        except Exception as e:
            print(f"Error during document search: {e}")
            return False, [], []

    def get_context_for_query(self, query: str) -> Optional[str]:
        """
        Get formatted context for a query, or None if not relevant enough.
        """
        is_relevant, documents, scores = self.search_documents(query)

        if not is_relevant or not documents:
            return None

        # Format context from relevant documents
        context_parts = []
        for doc, score in zip(documents, scores):
            if score >= self.relevance_threshold:
                context_parts.append(doc.content.strip())

        if not context_parts:
            return None

        # Join context with separators
        context = "\n\n---\n\n".join(context_parts)
        return context

    def set_relevance_threshold(self, threshold: float):
        """Set the minimum relevance threshold for document retrieval"""
        self.relevance_threshold = threshold
        print(f"Relevance threshold set to {threshold}")


# Global instance (singleton pattern for simplicity)
health_rag = HealthRAGService()
