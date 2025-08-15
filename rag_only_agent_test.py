from health_bot import HealthBotSession
from prompt_library import get_system_prompt

def test_rag_only():
    """Test the agent with RAG-only functionality"""
    
    # Test queries that should work with RAG
    test_queries = [
        "What are tension headache symptoms?",
        # "How can I prevent migraines?",
        # "What causes lower back pain?",
        # "How does stress affect pain?",
        # "What are the best treatments for neck pain?"
    ]
    
    # Test query that should NOT work (not in documents)
    out_of_scope_query = "What are the symptoms of diabetes?"
    
    print("Testing RAG-Only Agent")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n🔍 Testing: {query}")
        print("-" * 40)
        
        try:
            session = HealthBotSession(query)
            conversation = session.run_conversation()
            
            # Get the first response
            response = next(conversation)
            print(f"✅ Response received (length: {len(response)} chars)")
            print(response[:200] + "..." if len(response) > 200 else response)
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Test out-of-scope query
    print(f"\n🚫 Testing out-of-scope: {out_of_scope_query}")
    print("-" * 40)
    
    try:
        session = HealthBotSession(out_of_scope_query)
        conversation = session.run_conversation()
        response = next(conversation)
        print(f"📄 Response: {response}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_rag_only()
