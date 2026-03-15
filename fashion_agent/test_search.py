import json
from search.search_engine import search

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

for q in queries:
    print(f"\n{'='*50}")
    print(f"Query: {q}")
    print(f"{'='*50}")
    
    results = search(q, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"{i}. {r.label} - {r.color}")
        print(f"   Score: {r.score:.4f}")
        print(f"   Caption: {r.caption[:100]}...")
