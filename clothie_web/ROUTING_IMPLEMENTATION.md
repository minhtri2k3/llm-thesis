# Flutter Routing Implementation with go_router

## Problem
The Flutter app was manually passing `userName` and `sessionId` through constructor parameters using `Navigator.pushReplacement()`, which could cause issues with:
- State management and data persistence
- Navigation history and back button behavior
- Deep linking and URL-based navigation
- Code maintainability as the app grows

## Solution
Implemented `go_router` — the official recommended routing package for Flutter apps, providing:
- ✓ Declarative routing with named routes
- ✓ Type-safe parameter passing
- ✓ URL-based navigation (essential for web)
- ✓ Better state management
- ✓ Cleaner, more maintainable code

## Architecture

### Route Structure
```
/ (splash) → /register → /chat
```

### Files Created/Modified

#### 1. **New: `/lib/router/app_router.dart`**
Centralized router configuration with:
- Route definitions for all screens
- Type-safe route arguments (`ChatRouteArgs`)
- Error handling (404 page)
- Named routes for easy navigation

```dart
class ChatRouteArgs {
  final String sessionId;
  final String userName;
  // ...
}

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', name: 'splash', ...),
    GoRoute(path: '/register', name: 'register', ...),
    GoRoute(path: '/chat', name: 'chat', ...),
  ],
);
```

#### 2. **Modified: `/lib/main.dart`**
Changed from `MaterialApp` to `MaterialApp.router`:
```dart
MaterialApp.router(
  routerConfig: appRouter,  // ← Now uses go_router
  // ...
)
```

#### 3. **Modified: `/lib/screens/splash_screen.dart`**
```dart
// Before:
Navigator.of(context).pushReplacement(PageRouteBuilder(...));

// After:
context.goNamed('register');  // ← Clean, simple
```

#### 4. **Modified: `/lib/screens/register_screen.dart`**
```dart
// Before:
Navigator.of(context).pushReplacement(
  PageRouteBuilder(
    pageBuilder: (_, anim, __) => 
        ChatScreen(sessionId: sessionId, userName: name),
    // ...
  ),
);

// After:
context.goNamed(
  'chat',
  extra: ChatRouteArgs(
    sessionId: sessionId,
    userName: name,
  ),
);  // ← Type-safe, cleaner
```

#### 5. **Modified: `/lib/screens/chat_screen.dart`**
```dart
// Before:
Navigator.of(context).pushAndRemoveUntil(
  PageRouteBuilder(pageBuilder: (_, anim, __) => const SplashScreen()),
  (_) => false,
);

// After:
context.goNamed('splash');  // ← Much simpler
```

## Benefits

### 1. **Type-Safe Navigation**
Route parameters are strongly typed via `ChatRouteArgs`, preventing runtime errors.

### 2. **URL-Based Routing**
For web deployment, routes map to URLs:
- `https://yourapp.com/` → Splash screen
- `https://yourapp.com/register` → Register screen
- `https://yourapp.com/chat` → Chat screen

### 3. **Centralized Configuration**
All routes are defined in one place (`app_router.dart`), making it easy to:
- Add new screens
- Modify route paths
- Implement route guards/middleware
- Add authentication checks

### 4. **Better State Management**
`go_router` integrates well with Flutter's state management solutions and doesn't interfere with Provider, Bloc, etc.

### 5. **Error Handling**
Built-in 404 error page for invalid routes.

### 6. **Deep Linking Support**
Easy to implement deep links for:
- Sharing specific chat sessions
- Email links to resume conversations
- Marketing campaigns with pre-filled data

## Usage Examples

### Navigate to Chat
```dart
context.goNamed(
  'chat',
  extra: ChatRouteArgs(
    sessionId: 'abc123',
    userName: 'John',
  ),
);
```

### Navigate Back to Splash
```dart
context.goNamed('splash');
```

### Access Route Parameters
Parameters are passed to the screen via constructor as before:
```dart
class ChatScreen extends StatefulWidget {
  final String sessionId;
  final String userName;
  
  const ChatScreen({
    required this.sessionId,
    required this.userName,
  });
}
```

## Dependencies Added

```yaml
dependencies:
  go_router: ^14.2.0
```

## Testing

To test the routing:
1. Run the app: `flutter run -d chrome`
2. Splash screen appears → auto-navigates to Register after 3 seconds
3. Fill in name, year, gender → click "Start Chatting"
4. Navigates to Chat screen with proper sessionId and userName
5. Click "End Session" → rating dialog → navigates back to Splash
6. All navigation works smoothly with proper state management

## Future Enhancements

With go_router in place, you can easily add:
- **Route guards**: Protect routes that require authentication
- **Nested navigation**: Tab bars, side menus with sub-routes
- **Query parameters**: `?tab=settings` style URLs
- **Path parameters**: `/chat/:sessionId` for shareable links
- **Redirect logic**: Auto-redirect based on session state
- **Transitions**: Custom page transition animations

## Migration Notes

The migration from manual Navigator to go_router was straightforward:
- ✓ No breaking changes to existing screen components
- ✓ Constructor parameters still work the same way
- ✓ Provider state management unaffected
- ✓ All existing functionality preserved
- ✓ Code is cleaner and more maintainable
