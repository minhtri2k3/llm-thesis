/// App-wide configuration constants.
///
/// API base URL is intentionally empty so all requests use relative paths
/// (e.g., `/api/chat/stream`). Nginx reverse-proxies `/api/*` to fashion-api.
library;

const String kApiBaseUrl = '';

const int kSplashDurationSeconds = 2;
const int kMaxStarRating = 10;
