## 1. Routing and Access Flow

- [x] 1.1 Add a dedicated professor dashboard route in `clothie_web/lib/router/app_router.dart`.
- [x] 1.2 Refactor Professor View entry in `register_screen.dart` to navigate to the new page after successful PIN validation.
- [x] 1.3 Preserve protected-access behavior by blocking navigation when admin-key validation fails.

## 2. Analytics Data Wiring

- [x] 2.1 Add/extend API service methods to fetch behavior funnel, token usage, and demographics for professor charts.
- [x] 2.2 Implement frontend adapter models that transform backend analytics payloads into chart series + KPI card data.
- [x] 2.3 Add null/empty-safe mapping for missing integrity fields and zero-activity path segments.

## 3. Professor Chart Page UI

- [x] 3.1 Create a new professor analytics page widget with full-page layout and sectioned chart containers.
- [x] 3.2 Implement PATH 1 vs PATH 2 comparative charts for funnel metrics and rates.
- [x] 3.3 Add token and session summary cards for thesis presentation context.
- [x] 3.4 Add integrity warning badges and issue summary blocks alongside comparative charts.

## 4. Flutter Web Chart Reliability

- [x] 4.1 Integrate one Flutter chart library with solid web support and wire tooltip/legend interactions.
- [x] 4.2 Implement responsive chart resizing behavior for desktop presentation breakpoints.
- [x] 4.3 Implement fallback table/summary rendering when chart components fail to initialize.

## 5. Verification and Release Readiness

- [x] 5.1 Validate professor page behavior for loading, empty, error, and unauthorized states.
- [x] 5.2 Validate visual correctness for path comparison and integrity highlighting on Flutter Web browsers.
- [x] 5.3 Confirm existing professor analytics flows remain backward compatible after route/page migration.
