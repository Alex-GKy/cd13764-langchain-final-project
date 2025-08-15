import os
from haystack import Pipeline, Document
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter
from haystack.components.embedders import OpenAIDocumentEmbedder, \
    OpenAITextEmbedder
from haystack.components.writers import DocumentWriter
from haystack.components.retrievers import InMemoryEmbeddingRetriever
from haystack.components.generators import OpenAIGenerator
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore

# Set your OpenAI API key
from dotenv_loader import api_key

os.environ["OPENAI_API_KEY"] = api_key


def main():
    # 1. Initialize document store
    document_store = InMemoryDocumentStore()

    # 2. Create indexing pipeline to load PDFs
    indexing_pipeline = Pipeline()
    indexing_pipeline.add_component("converter", PyPDFToDocument())
    indexing_pipeline.add_component("cleaner", DocumentCleaner())
    indexing_pipeline.add_component("splitter",
                                    DocumentSplitter(split_by="sentence",
                                                     split_length=3))
    indexing_pipeline.add_component("embedder", OpenAIDocumentEmbedder())
    indexing_pipeline.add_component("writer", DocumentWriter(
        document_store=document_store))

    # Connect the components
    indexing_pipeline.connect("converter", "cleaner")
    indexing_pipeline.connect("cleaner", "splitter")
    indexing_pipeline.connect("splitter", "embedder")
    indexing_pipeline.connect("embedder", "writer")

    # 3. Load all PDFs from health_pdfs folder
    pdf_files = [f"health_pdfs/{f}" for f in os.listdir("health_pdfs") if
                 f.endswith('.pdf')]
    print(f"Loading {len(pdf_files)} PDFs...")

    indexing_pipeline.run({"converter": {"sources": pdf_files}})
    print(f"Indexed {document_store.count_documents()} document chunks")

    # 4. Create RAG pipeline
    rag_pipeline = Pipeline()
    rag_pipeline.add_component("text_embedder", OpenAITextEmbedder())
    rag_pipeline.add_component("retriever", InMemoryEmbeddingRetriever(
        document_store=document_store))
    rag_pipeline.add_component("prompt_builder", PromptBuilder(
        template="""
        Answer the question based on the provided context.
        
        Context:
        {% for document in documents %}
            {{ document.content }}
        {% endfor %}
        
        Question: {{ question }}
        Answer:
        """
    ))
    rag_pipeline.add_component("llm", OpenAIGenerator())

    # Connect RAG components
    rag_pipeline.connect("text_embedder.embedding",
                         "retriever.query_embedding")
    rag_pipeline.connect("retriever", "prompt_builder.documents")
    rag_pipeline.connect("prompt_builder", "llm")

    # 5. Test with a simple query
    question = "What are the main causes of leper?"
    print(f"\nQuestion: {question}")

    result = rag_pipeline.run({
        "text_embedder": {"text": question},
        "prompt_builder": {"question": question}
    })

    print(f"Answer: {result['llm']['replies'][0]}")


if __name__ == "__main__":
    main()
