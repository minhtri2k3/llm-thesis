## 1. Database Migration (Backend)

- [x] 1.1 In `fashion_agent/agent/memory.py` → `init_memory_tables()`: add `ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS year_of_birth INT;`
- [x] 1.2 In `init_memory_tables()`: add `ALTER TABLE user_sessions ADD COLUMN IF NOT EXISTS gender TEXT CHECK (gender IN ('male', 'female'));`
- [x] 1.3 Update `create_session(user_name, year_of_birth, gender)` to accept and persist the two new params in the `INSERT INTO user_sessions` statement

## 2. Backend API — Session Creation (FastAPI)

- [x] 2.1 In `fashion_agent/api/main.py`: add `year_of_birth: Optional[int] = None` and `gender: Optional[str] = None` to `CreateSessionRequest` with Pydantic validators (1900 ≤ year ≤ current year; gender must be `"male"` or `"female"` if provided)
- [x] 2.2 Update `create_session_endpoint` to pass `year_of_birth` and `gender` through to `create_session()`

## 3. Backend API — Demographics & Rating Endpoints (FastAPI)

- [x] 3.1 In `GET /api/ratings`: JOIN `user_sessions` to include `year_of_birth` and `gender` in each response entry
- [x] 3.2 Add `GET /api/demographics` endpoint (protected by `X-Admin-Key`) that returns `by_gender` and `by_age_group` aggregates (avg. rating, count) using a SQL CASE expression for age buckets
- [x] 3.3 Add `DemographicsResponse` Pydantic model for the new endpoint

## 4. Flutter — API Service

- [x] 4.1 In `clothie_web/lib/services/api_service.dart`: update `createSession(String userName)` to `createSession(String userName, int yearOfBirth, String gender)` and include `year_of_birth` and `gender` in the JSON body
- [x] 4.2 Add `getDemographics(String secretKey)` method that calls `GET /api/demographics` with `X-Admin-Key` header

## 5. Flutter — Register Screen UI

- [x] 5.1 In `clothie_web/lib/screens/register_screen.dart`: add `_yearController` (`TextEditingController`) for birth year input below the name field
- [x] 5.2 Add a binary gender toggle (two styled buttons: "Boy 👦" / "Girl 👧") that sets `_selectedGender` state
- [x] 5.3 Add UI-side validation in `_startChat()`: birth year must be parseable int in range 1900–current year; gender must be selected
- [x] 5.4 Update `_startChat()` call to `_api.createSession(name, yearOfBirth, gender)` with the validated values
- [x] 5.5 Update subtitle copy from "Tell us your name to get started" to "Tell us a bit about yourself to get started"

## 6. Flutter — Professor View Demographics Panel

- [x] 6.1 In `clothie_web/lib/screens/register_screen.dart` → `_ProfessorDashboardDialog`: add a second section below token analytics titled "📊 Demographics"
- [x] 6.2 Call `_api.getDemographics(secretKey)` during `_load()` and store result in state
- [x] 6.3 Render `by_gender` rows (Male / Female avg. rating + count) in the panel
- [x] 6.4 Render `by_age_group` rows (Under 20 / 20-29 / 30-39 / 40+ avg. rating + count)
- [x] 6.5 Show "No demographic data yet" placeholder when arrays are empty

## 7. Docker Rebuild & Verification

- [x] 7.1 Run `docker compose up --build -d` from `fashion_agent/` to rebuild the backend image with new code
- [x] 7.2 Run `docker compose logs -f api` and verify `Memory tables initialized.` appears without errors
- [x] 7.3 Confirm `year_of_birth` and `gender` columns exist: `docker compose exec db psql -U fashion_user -d fashion_rag -c "\d user_sessions"`
- [x] 7.4 Test `POST /api/sessions` with `{"user_name":"Test","year_of_birth":1998,"gender":"female"}` and confirm `200 OK`
- [x] 7.5 Test `POST /api/sessions` with invalid year (`year_of_birth: 1800`) and confirm `422` response
- [x] 7.6 Test `GET /api/demographics` with valid `X-Admin-Key` and confirm response structure
- [x] 7.7 Run `flutter run -d web-server` (or rebuild Flutter Docker image) and verify the new register form fields work end-to-end
