# Clothie Web - Frontend Meta-Prompt & System Design

**Role**: You are a Frontend UI Agent assigned to build or extend the `clothie_web` Flutter web application.

**Purpose of this Document**: This document outlines the exact state management logic, API integration methods, and UI components currently implemented in the frontend. Before adding new logic, assume the underlying services and state managers below provide the capabilities you need.

---

## 1. Network & Data Layer (`lib/services/api_service.dart`)

The `ApiService` handles all communication with the Python Backend API. All calls return parsed JSON maps or standard dart objects.

**Implemented Methods:**
- `createSession(String userName, String gender, String preferredModel) -> Future<String>` 
  *Creates a new tracking session. Sends user profile along with LLM preference (Gemini/GPT-4o/Claude). Returns `sessionId`.*
  
- `searchProducts(String sessionId, String query) -> Future<List<Product>>` 
  *Retrieves fashion items matching the search query.*
  
- `chatRequest(String sessionId, List<Map<String, dynamic>> messages, List<Product> selectedItems) -> Stream<String>`
  *Sends user chat and current wardrobe cart state. Yields SSE streaming chunks from the AI.*
  
- `trackClick(String sessionId, String imageId) -> Future<void>`
  *Fires analytics event when a product is viewed/tapped.*
  
- `logIntent(String sessionId, String imageId, String intentType) -> Future<void>`
  *Logs buying intent ('will_buy', 'not_for_me').*

- `removeCartItem(String sessionId, String imageId) -> Future<void>`
  *Removes an item from the confirmed cart on the backend.*
  
- `submitRating(String sessionId, int rating, String feedback) -> Future<void>`
  *Submits end-of-session evaluation (1-10 stars).*
  
- `getRatings() -> Future<List<Map<String, dynamic>>>`
  *Fetches metrics for the Leaderboard (scores, participants, chosen models, token counts).*

---

## 2. State Management (`lib/providers/`)

The app uses Flutter's `provider` package to manage overarching UI state.

**`CartProvider` (`cart_provider.dart`)**
- `items`: The current `List<CartItem>` selected/favorite items.
- `count`: Gets length of the current cart list.
- `add(CartItem item)`: Add a new item to cart via UI state.
- `remove(String imageId)`: Removes specific product locally.
- `clear()`: Purges completely.
- `reload()`: Dispatches UI update signals to listeners. **Important**: Always call `reload()` after backend removals.

**`ChatProvider` (`chat_provider.dart`)**
- Maintains history of `ChatMessage`.
- Manages auto-scrolling logic and streaming text chunk concatenation.

**`ThemeProvider` (`theme_provider.dart`)**
- Governs Dark/Light mode state.

---

## 3. UI Screens & Their Business Logics (`lib/screens/`)

**`RegisterScreen`**
- Manages starting state (Username input, Gender selection).
- Contains a segment control/button row for LLM Model Picker.
- Calls `createSession` and routes to `ChatScreen`.
- Houses the `_LeaderboardDialog` popup which reads ratings and formats the LLM `model_name` chip + `total_tokens`.

**`ChatScreen`**
- Core view containing Chat Feed and side-by-side components.
- Uses `_buildChatList()` and list controllers for infinite scroll dynamics.
- Connects the chat input textfield to `api.chatRequest(...)`.

**`CartScreen`**
- Intercepts items stored in `CartProvider`.
- Contains `_CartCard` widget which has two tracking operations:
   - `_logIntent()`: Track user intention status.
   - `_removeItem()`: Hits `ApiService.removeCartItem()`, and updates the cart badge.

**`ProductCard` (`lib/widgets/product_card.dart`)**
- Renders individual clothing product.
- **Interactions**:
   1. Tracks clicks via `trackClick()`.
   2. Opens `_showFullscreenImage()` Dialog popup overlaying `InteractiveViewer` over `Image.network` allowing pinch-to-zoom over a dark barrier.

---

## Agent Instructions:
1. Do not duplicate networking requests. If a component needs to drop an item, use `ApiService.removeCartItem` and invoke `CartProvider.reload()`.
2. Do not invent your own HTTP calls. The backend logic handles intent tracking securely, simply pass the existing `sessionId`.
3. Use the built-in theme (`Theme.of(context).colorScheme`) for all styling, avoid hardcoded hex codes. Follow the sleek, premium glassmorphism layouts implemented across the app.
