/// App-wide configuration constants.
///
/// API base URL is intentionally empty so all requests use relative paths
/// (e.g., `/api/chat/stream`). Nginx reverse-proxies `/api/*` to fashion-api.
library;

const String kApiBaseUrl = '';

const int kSplashDurationSeconds = 2;
const int kMaxStarRating = 10;

/// Dark color palette for Clothie
const int kBgColor = 0xFF0D0D14;
const int kSurfaceColor = 0xFF1A1A2E;
const int kCardColor = 0xFF16213E;
const int kAccentColor = 0xFF7C3AED; // violet-600
const int kAccentLight = 0xFFA78BFA; // violet-400
const int kUserBubbleColor = 0xFF4C1D95;
const int kTextPrimary = 0xFFF8F9FA;
const int kTextSecondary = 0xFFADB5BD;
