import json
import asyncio
from agent.fashion_agent import chat

queries = [
    # Keyword
    "Shoes",
    "Áo thun màu trắng",
    
    # Semantic/Vibe
    "A dress for a summer beach party",
    "Đồ mặc đi làm mùa đông",

    # Multi-constraint
    "Black leather jacket with zippers",
    "Áo khoác màu đen có túi"
]

def run_tests():
    for q in queries:
        print(f"\n{'='*50}")
        print(f"User: {q}")
        print(f"{'='*50}")
        
        # Test full ReAct agent
        response = chat(q)
        print(f"Agent Reasoning: {response.reasoning}")
        print(f"\nAgent Answer: {response.answer}")
        
        if response.products:
            print(f"\nTop Products Returned:")
            for i, p in enumerate(response.products[:3], 1):
                print(f"  {i}. {p.label} - {p.color} (Score: {p.score:.4f})")
                print(f"     Caption: {p.caption[:100]}...")

if __name__ == "__main__":
    run_tests()
