## Why

The current Professor View is a dialog with tabular token data, which is hard to present as clear thesis evidence for PATH 1 vs PATH 2 quality. We need a dedicated professor analytics page with high-clarity charts and integrity signals so evaluation results are more defensible and visually persuasive.

## What Changes

- Add a dedicated professor-only page (separate route) instead of relying on an in-register dialog for analytics review.
- Add chart-first visualizations for thesis metrics, including PATH 1 vs PATH 2 funnel comparison, integrity status, and token usage summaries.
- Add chart-ready API payload structure (or adapters) so frontend rendering is stable and consistent for Flutter Web.
- Preserve admin-key protection for professor analytics access and reuse existing telemetry integrity semantics.

## Capabilities

### New Capabilities
- `professor-chart-dashboard`: Dedicated professor page that presents thesis analytics using chart visualizations and summary cards.
- `path-comparison-visualization`: Standardized comparative analytics views for PATH 1 and PATH 2 funnel stages, conversion, and integrity quality indicators.
- `flutter-web-chart-rendering`: Frontend chart rendering strategy for Flutter Web with consistent behavior and fallback handling for unsupported chart interactions.

### Modified Capabilities
- None.

## Impact

- Frontend: `clothie_web/lib/router/app_router.dart`, `clothie_web/lib/screens/register_screen.dart`, new professor chart page widgets, and `clothie_web/lib/services/api_service.dart`.
- Backend: `fashion_agent/api/main.py` analytics endpoints (especially behavior funnel response shaping) and potentially `fashion_agent/api/analytics.py` for chart-focused aggregates.
- Data contract: chart-oriented response fields for PATH comparison, integrity breakdown, and token summary cards.
- Dependencies: add a Flutter charting package suitable for Flutter Web rendering quality and interaction needs.
