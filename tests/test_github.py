import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.openai_provider import OpenAIProvider

def test_github_api():
    load_dotenv()
    
    # We are using GitHub Models mapped via OpenAI library.
    print(f"--- Testing Provider with GitHub Token ---")
    
    try:
        provider = OpenAIProvider(model_name="gpt-4o")
        
        prompt = "Explain what an AI Agent is in one sentence."
        print(f"\nUser: {prompt}")
        print("Assistant: ", end="", flush=True)
        
        # We can test generate
        response = provider.generate(prompt)
        print(response['content'])
        
        print("\n\n✅ Provider is working correctly with GitHub API!")
        
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")

if __name__ == "__main__":
    test_github_api()
