## 1. Pricing data model and policy setup

- [ ] 1.1 Add optional `price_cents` support to catalog and selection persistence models.
- [ ] 1.2 Create category pricing policy structure (baseline and bounded variation constraints).
- [ ] 1.3 Define null-safe read/write behavior for records without price during transition.

## 2. Backfill and indexing propagation

- [ ] 2.1 Implement one-time backfill job to generate stable per-item prices from category policy.
- [ ] 2.2 Add completeness checks and reporting for backfill coverage by category.
- [ ] 2.3 Propagate `price_cents` into indexing payloads and retrieval data structures.

## 3. Backend and agent price-intent behavior

- [ ] 3.1 Extend intent extraction to detect budget/premium price preference and optional price constraints.
- [ ] 3.2 Implement price-aware ranking overlay after relevance retrieval with fallback to relevance-only behavior.
- [ ] 3.3 Expose optional price fields in API responses used by search, product details, and session selections.

## 4. Frontend and UX compatibility

- [ ] 4.1 Extend frontend product and cart models with optional `price_cents` parsing.
- [ ] 4.2 Add null-safe price rendering in product cards and cart/selection views.
- [ ] 4.3 Keep behavior unchanged for payloads without price values.

## 5. Rollout safety, documentation, and evidence alignment

- [ ] 5.1 Define phased rollout gates (schema/backfill/index/backend/frontend) and rollback toggles.
- [ ] 5.2 Add regression checks for Path1/Path2 retrieval and non-price user journeys.
- [ ] 5.3 Update thesis/report sections to document pricing scope, migration strategy, and evaluation boundary changes.
