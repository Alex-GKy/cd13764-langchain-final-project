
from health_rag_service import HealthRAGService

def main():
    # Create service instance
    service = HealthRAGService()
    
    # Initialize the service
    if service.initialize():
        print("\n" + "="*50)
        print("TESTING HEALTH RAG SERVICE")
        print("="*50)
        
        # Test with diabetes query (should find no relevant documents)
        query = "What are the symptoms of diabetes?"
        print(f"\nQuery: {query}")

        service.set_relevance_threshold(0.8)
        # Get context for the query
        context = service.get_context_for_query(query)
        
        if context:
            print(f"\nFound relevant context:")
            print("-" * 30)
            print(context[:500] + "..." if len(context) > 500 else context)
        else:
            print("\n❌ No relevant documents found for this query.")
            print("The available health documents cover: headaches, migraines, back pain, neck pain, and stress management.")
            print("For diabetes information, you would need to add diabetes-related PDFs to the system.")
            
    else:
        print("Failed to initialize Health RAG Service!")

if __name__ == "__main__":
    main()
