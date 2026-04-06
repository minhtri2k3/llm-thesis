#!/usr/bin/env python3
"""Comprehensive test for multilingual confirm/reject keywords."""

import sys
sys.path.insert(0, '/Users/tringuyen/llm-thesis/fashion_agent')
from agent.fashion_agent import CONFIRM_KEYWORDS, REJECT_KEYWORDS

print("=" * 70)
print("Multilingual Confirmation Keywords Test")
print("=" * 70)

# Test cases organized by language
test_cases = {
    "English Confirm": {
        "keywords": ["yes", "ok", "okay", "sure", "yep", "yeah", "confirm", "save", "y"],
        "set": CONFIRM_KEYWORDS,
    },
    "English Reject": {
        "keywords": ["no", "cancel", "skip", "n", "nope"],
        "set": REJECT_KEYWORDS,
    },
    "Vietnamese Confirm": {
        "keywords": ["có", "vâng", "dạ", "ừ", "đúng", "đồng ý", "lưu", "được", "chốt", "oke"],
        "set": CONFIRM_KEYWORDS,
    },
    "Vietnamese Reject": {
        "keywords": ["không", "hủy", "thôi", "bỏ", "không lưu"],
        "set": REJECT_KEYWORDS,
    },
    "Spanish Confirm": {
        "keywords": ["sí", "si", "confirmar", "guardar", "claro", "dale", "bueno", "de acuerdo"],
        "set": CONFIRM_KEYWORDS,
    },
    "Spanish Reject": {
        "keywords": ["no", "cancelar", "cancela", "omitir", "quitar", "no gracias"],
        "set": REJECT_KEYWORDS,
    },
}

all_passed = True
results = []

for test_name, test_data in test_cases.items():
    print(f"\n{test_name}:")
    print("-" * 70)
    passed = 0
    failed = 0
    
    for keyword in test_data["keywords"]:
        normalized = keyword.strip().lower()
        is_match = normalized in test_data["set"]
        
        if is_match:
            print(f"  ✓ '{keyword}'")
            passed += 1
        else:
            print(f"  ✗ FAIL: '{keyword}' NOT FOUND!")
            failed += 1
            all_passed = False
    
    results.append((test_name, passed, failed))

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

for test_name, passed, failed in results:
    total = passed + failed
    status = "✓ PASS" if failed == 0 else "✗ FAIL"
    print(f"{status} {test_name}: {passed}/{total} keywords working")

print("\n" + "=" * 70)

if all_passed:
    print("✓ ALL TESTS PASSED - All three languages are fully supported!")
else:
    print("✗ SOME TESTS FAILED - Missing keywords detected!")
    
print("=" * 70)

# Additional edge case tests
print("\nEdge Case Tests:")
print("-" * 70)

edge_cases = [
    # Case insensitivity
    ("YES", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "English uppercase"),
    ("CÓ", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "Vietnamese uppercase"),
    ("SÍ", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "Spanish uppercase"),
    ("No", lambda k: k.strip().lower() in REJECT_KEYWORDS, True, "Mixed case"),
    
    # Whitespace handling
    ("  yes  ", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "Extra whitespace EN"),
    ("  có  ", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "Extra whitespace VI"),
    ("  sí  ", lambda k: k.strip().lower() in CONFIRM_KEYWORDS, True, "Extra whitespace ES"),
    ("  không  ", lambda k: k.strip().lower() in REJECT_KEYWORDS, True, "Extra whitespace VI reject"),
]

for test_input, check_func, expected, description in edge_cases:
    result = check_func(test_input)
    status = "✓" if result == expected else "✗"
    print(f"  {status} {description}: '{test_input}' -> {result}")
    if result != expected:
        all_passed = False

print("\n" + "=" * 70)
if all_passed:
    print("✓ COMPLETE SUCCESS - All languages and edge cases working!")
else:
    print("✗ ISSUES DETECTED - Review failures above")
print("=" * 70)

sys.exit(0 if all_passed else 1)
