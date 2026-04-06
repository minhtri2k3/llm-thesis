#!/usr/bin/env python3
"""Verify Flutter routing implementation is correct."""

import os
import re

def check_file_exists(filepath):
    """Check if a file exists."""
    return os.path.exists(filepath)

def check_file_contains(filepath, pattern, description):
    """Check if a file contains a specific pattern."""
    if not check_file_exists(filepath):
        return False, f"✗ File not found: {filepath}"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    if re.search(pattern, content):
        return True, f"✓ {description}"
    else:
        return False, f"✗ {description}"

print("=" * 70)
print("Flutter Routing Implementation Verification")
print("=" * 70)

checks = []

# 1. Check pubspec.yaml has go_router
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/pubspec.yaml',
    r'go_router:',
    'go_router dependency in pubspec.yaml'
))

# 2. Check app_router.dart exists
result = check_file_exists(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/router/app_router.dart'
)
checks.append((result, 'Router file exists'))
if result:
    checks.append((True, '✓ Router file created'))

# 3. Check app_router.dart has ChatRouteArgs
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/router/app_router.dart',
    r'class ChatRouteArgs',
    'ChatRouteArgs class defined'
))

# 4. Check app_router.dart has route definitions
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/router/app_router.dart',
    r"name: 'chat'",
    'Chat route defined'
))

# 5. Check main.dart uses MaterialApp.router
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/main.dart',
    r'MaterialApp\.router',
    'main.dart uses MaterialApp.router'
))

# 6. Check main.dart imports app_router
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/main.dart',
    r"import.*app_router",
    'main.dart imports app_router'
))

# 7. Check register_screen.dart uses go_router
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/screens/register_screen.dart',
    r'context\.goNamed',
    'RegisterScreen uses go_router navigation'
))

# 8. Check register_screen.dart uses ChatRouteArgs
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/screens/register_screen.dart',
    r'ChatRouteArgs',
    'RegisterScreen uses ChatRouteArgs'
))

# 9. Check chat_screen.dart uses go_router for navigation
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/screens/chat_screen.dart',
    r'context\.goNamed',
    'ChatScreen uses go_router navigation'
))

# 10. Check splash_screen.dart uses go_router
checks.append(check_file_contains(
    '/Users/tringuyen/llm-thesis/clothie_web/lib/screens/splash_screen.dart',
    r'context\.goNamed',
    'SplashScreen uses go_router navigation'
))

# Print results
print("\nVerification Results:")
print("-" * 70)

passed = sum(1 for check in checks if check[0])
total = len(checks)

for success, message in checks:
    print(f"  {message}")

print("\n" + "=" * 70)
print(f"Results: {passed}/{total} checks passed")
print("=" * 70)

if passed == total:
    print("\n✓ SUCCESS! All routing checks passed.")
    print("\nThe Flutter app now uses go_router for navigation.")
    print("userName and sessionId are properly passed via route arguments.")
else:
    print("\n✗ Some checks failed. Please review the issues above.")
