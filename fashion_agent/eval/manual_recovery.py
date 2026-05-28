"""5 cart-adds from May 1 sessions whose impression logs were missing.

Refined queries reconstructed from conversation_history user messages,
following the same '[modifier] [Category]' pattern observed in the
19 recovered-from-impressions cases.
"""

MANUAL_CASES = [
    {
        "session_id": "db205850-f9f5-4ea3-9616-3bb423e25ad8",
        "picked_id": "094a6288-3fe1-4422-9912-c2f2704fe067",
        "query": "black Blazer",
        "raw_user_message": "I want the black blazer , find me other blazer",
        "pick_position": 1,
    },
    {
        "session_id": "7605dfc7-1e38-4bf4-9a68-e6d98a1a63b3",
        "picked_id": "c7f0e9ee-507b-4b89-b7d1-7669a680560e",
        "query": "white Blazer",
        "raw_user_message": "I want to buy a blazer with white color",
        "pick_position": 5,
    },
    {
        "session_id": "7605dfc7-1e38-4bf4-9a68-e6d98a1a63b3",
        "picked_id": "10114489-5e19-4de3-8dbb-6c9d69675b77",
        "query": "white Blazer",
        "raw_user_message": "Also add 1 and 3 (from same result-set as previous)",
        "pick_position": 0,
    },
    {
        "session_id": "7605dfc7-1e38-4bf4-9a68-e6d98a1a63b3",
        "picked_id": "67242183-82be-491d-84cb-cd0ae9d00e19",
        "query": "white Blazer",
        "raw_user_message": "Also add 1 and 3 (from same result-set as previous)",
        "pick_position": 0,
    },
    {
        "session_id": "abdfcb54-43ec-48a9-a3ec-5957392dc5c7",
        "picked_id": "5a8598c8-3756-4bb7-8e22-4bdefe86c18d",
        "query": "dating Outfit",
        "raw_user_message": "Give me some clothe for dating",
        "pick_position": 4,
    },
]
