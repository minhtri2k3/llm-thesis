## Context

The current chat orchestration favors search-first behavior for `text_search` and `follow_up`, which can generate recommendations before enough intent detail is collected. At the same time, PATH 2 cart-add behavior currently depends on conversational selection parsing (numeric select + confirm), which is fragile because PATH 2 search results are not part of the same conversational result history contract used by intent classification.

Stakeholders:
- End users who expect clarifying questions before weak recommendations.
- Product/thesis evaluation stakeholders who need reliable add-to-cart signals for PATH 2.
- Engineering team maintaining both PATH 1 (chat) and PATH 2 (image search) flows.

Constraints:
- Preserve existing PATH 1 selection-confirm flow behavior.
- Keep path attribution (`path_mode`) consistent for analytics.
- Minimize schema churn by reusing existing selection persistence where possible.

## Goals / Non-Goals

**Goals:**
- Enforce pre-search readiness gating for search-like intents using confidence and slot completeness.
- Prevent query execution when required intent details are missing.
- Introduce a dedicated PATH 2 add-to-cart contract that does not rely on LLM intent parsing.
- Ensure PATH 2 direct adds are persisted and visible in cart/analytics with `path_mode=path2`.

**Non-Goals:**
- Redesigning recommendation ranking or retrieval quality logic.
- Replacing PATH 1 conversational selection-confirm UX.
- Changing checkout/order semantics.
- Backfilling historical PATH 2 sessions.

## Decisions

1. **Pre-search readiness gate for search intents**
   - Apply readiness checks before search execution for `text_search` and `follow_up`.
   - Gate checks include:
     - Intent confidence threshold.
     - Slot completeness threshold (required slots from the slot completeness policy).
   - If either check fails, the system returns a clarification question and skips search execution.
   - **Alternative considered:** keep post-search clarification only.
   - **Why rejected:** still produces premature recommendations and noisy first-pass results.

2. **Keep slot completeness policy centralized**
   - Continue using shared slot completeness + template question builders as the canonical readiness policy.
   - **Alternative considered:** duplicate gating logic inside orchestration branches.
   - **Why rejected:** duplication risks drift between readiness checks and question templates.

3. **Dedicated direct cart-add contract for PATH 2**
   - Add a direct API contract for cart insertion (`POST /api/sessions/{session_id}/selections`) carrying explicit product payload and `path_mode`.
   - PATH 2 UI add-to-cart actions call this endpoint directly.
   - **Alternative considered:** keep PATH 2 on conversational numeric selection + confirm.
   - **Why rejected:** conversational classification is less deterministic for PATH 2-only interactions.

4. **Reuse existing selection persistence path**
   - The direct PATH 2 endpoint writes through existing selection persistence primitives (`save_selected_items`) and uniqueness constraints.
   - **Alternative considered:** add a new PATH 2-only cart table.
   - **Why rejected:** unnecessary duplication and fragmented analytics.

5. **Backward-compatible PATH split**
   - PATH 1 remains conversational and unchanged in UX; PATH 2 uses direct-add semantics.
   - Both flows continue emitting consistent path-attributed telemetry.

## Risks / Trade-offs

- **[Risk] Overly strict confidence threshold can increase clarification turns** → **Mitigation:** configure threshold and validate with acceptance tests for common short queries.
- **[Risk] Direct-add endpoint may be called with incomplete payloads** → **Mitigation:** strict request validation and explicit 4xx responses.
- **[Risk] Divergent PATH 1 vs PATH 2 add semantics can confuse maintainers** → **Mitigation:** document flow boundaries in API and tests with path-specific cases.
- **[Risk] Duplicate add attempts from rapid taps** → **Mitigation:** rely on existing idempotent uniqueness constraints and return inserted/skipped counts.

## Migration Plan

1. Introduce and validate the new direct selection API contract.
2. Wire PATH 2 UI add-to-cart action to direct API call and cart refresh.
3. Re-enable pre-search readiness gate in orchestration for `text_search` and `follow_up`.
4. Add/adjust tests for:
   - confidence + slot gating before query execution,
   - PATH 2 direct add success and invalid payload handling,
   - telemetry/path attribution consistency.
5. Roll out with monitoring for clarification rate and PATH 2 cart conversion.

Rollback strategy:
- Feature-flag or branch-guard the direct PATH 2 cart call and gating behavior so each can be toggled independently.
- If regressions occur, revert PATH 2 to current conversational selection flow and relax gating to previous behavior.

## Open Questions

- What default confidence threshold best balances fewer premature queries vs conversation friction?
- Should the direct selection endpoint be PATH 2-only initially or path-agnostic from day one?
- Should the API return both `inserted` and `already_exists` counts for better UX messaging?
