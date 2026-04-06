#!/usr/bin/env python3
"""Test script to verify confirm keyword matching for Vietnamese."""

import sys
sys.path.insert(0, '/Users/tringuyen/llm-thesis/fashion_agent')
from agent.fashion_agent import CONFIRM_KEYWORDS, REJECT_KEYWORDS

test_confirm = ["vâng", "có", "ok", "yes", "dạ", "ừ", "đồng ý", "chốt"]
test_reject = ["không", "no", "hủy", "bỏ"]

print("Testing CONFIRM keywords:")
print("=" * 60)
for test in test_confirm:
    normalized = test.strip().lower()
    is_match = normalized in CONFIRM_KEYWORDS
    status = "✓" if is_match else "✗ FAIL"
    print(f"{status} '{test}' -> '{normalized}' in CONFIRM: {is_match}")

print("\nTesting REJECT keywords:")
print("=" * 60)
for test in test_reject:
    normalized = test.strip().lower()
    is_match = normalized in REJECT_KEYWORDS
    status = "✓" if is_match else "✗ FAIL"
    print(f"{status} '{test}' -> '{normalized}' in REJECT: {is_match}")
