## Context

The current professor analytics surface is embedded as a modal dialog on `RegisterScreen`, optimized for quick inspection of token rows rather than thesis presentation. The backend already provides path-aware funnel and integrity data (`/api/analytics/behaviour-funnel`) and token analytics (`/api/analytics/token-usage`), but the frontend does not yet present these as comparative charts on a dedicated page.

Stakeholders:
- Thesis evaluator (needs clear, credible visuals and confidence signals)
- Student presenter (needs stable, fast demo flow)
- Engineering team (needs low-risk reuse of existing analytics contracts)

Constraints:
- Access must remain admin-protected using existing `X-Admin-Key` flow.
- Flutter Web must render charts reliably in projector/demo environments.
- Existing analytics endpoints should be reused before adding new backend complexity.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated professor page for analytics review (separate route/screen).
- Render chart-first PATH 1 vs PATH 2 comparisons with integrity context.
- Surface token and demographic summary blocks in the same page for thesis narrative continuity.
- Keep API and auth model backward compatible with current professor tooling.

**Non-Goals:**
- Replacing or removing current backend telemetry integrity logic.
- Building a generic BI/report-builder system.
- Introducing full user-auth RBAC beyond the existing admin-key model.
- Reworking recommendation/ranking algorithms.

## Decisions

1. **Use a dedicated professor route instead of dialog-first analytics.**  
   The professor dashboard will be a standalone page so charts, legends, and summaries can use full viewport width.  
   **Alternative considered:** keep improving modal dialog only.  
   **Why rejected:** modal constraints limit chart readability and “presentation quality.”

2. **Use one chart library with strong Flutter Web support and keep table fallback.**  
   The frontend should adopt a chart package suitable for web rendering and interaction (tooltips, legends, responsive resizing), while preserving a simple table fallback for resilience.  
   **Alternative considered:** custom canvas charts from scratch.  
   **Why rejected:** higher maintenance and increased risk for demo stability.

3. **Use API adapter/view-model mapping on frontend before backend schema changes.**  
   The page will map existing analytics payloads (`behaviour-funnel`, `token-usage`, demographics) into chart series and KPI cards. Backend changes are only added when a required chart field is missing.  
   **Alternative considered:** redesign all analytics endpoints first.  
   **Why rejected:** slower delivery and unnecessary migration risk.

4. **Retain current professor access gating with reusable PIN flow.**  
   The existing admin key validation remains the control point; PIN entry on register routes to professor page only after successful validation.  
   **Alternative considered:** temporary unprotected route for demos.  
   **Why rejected:** weakens confidentiality and deviates from existing security expectations.

5. **Represent integrity as first-class visualization state.**  
   Each path comparison view must include machine-readable integrity outcomes (valid/invalid, issue counts) and visually indicate non-actionable segments.  
   **Alternative considered:** keep integrity in raw JSON only.  
   **Why rejected:** users can misinterpret charts without visible data quality status.

## Risks / Trade-offs

- **[Risk] Web chart package increases bundle size** → **Mitigation:** choose one library, lazy-load professor page route, and avoid redundant chart dependencies.
- **[Risk] Data shape drift between endpoints and chart expectations** → **Mitigation:** add typed adapter layer with explicit null/default handling.
- **[Risk] Integrity-invalid segments still look persuasive** → **Mitigation:** enforce warning badges and reduced-emphasis styling for invalid segments.
- **[Risk] PIN re-entry hurts demo flow** → **Mitigation:** keep session-scoped in-memory key while app is open, without persisting secrets.

## Migration Plan

1. Add professor route and page shell while keeping current dialog entry point.
2. Introduce chart rendering layer and map existing endpoint payloads to chart models.
3. Add integrity badges/warnings and fallback table rendering.
4. Route Professor View CTA to the dedicated page after successful PIN validation.
5. Validate behavior on Flutter Web breakpoints and common presentation resolutions.
6. Keep rollback path by switching CTA back to existing dialog if needed.

## Open Questions

- Should invalid integrity segments be hidden by default or shown with warning styling?
- Which chart types best support thesis narration for PATH comparison (grouped bars only vs mixed bar+line)?
- Should professor page support a “download image/PDF” export for thesis appendix material?
