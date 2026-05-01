## 1. PATH 2 API Surface and Guardrails

- [ ] 1.1 Add dedicated PATH 2 image-query endpoint and request/response schema (separate from PATH 1 routes).
- [ ] 1.2 Add PNG validation rules and explicit error responses for unsupported uploads.
- [ ] 1.3 Add PATH 2 feature flag and disabled-state response behavior.

## 2. Isolated PATH 2 Retrieval Pipeline

- [ ] 2.1 Create separate PATH 2 retrieval module/function for image-query execution.
- [ ] 2.2 Wire FashionSigLIP image embedding query flow for PATH 2 without modifying PATH 1 `search()` behavior.
- [ ] 2.3 Add bounded runtime protections for PATH 2 requests (input size/runtime safety).

## 3. Frontend Separation for PATH 2 Entry

- [ ] 3.1 Add a distinct PATH 2 UI entry path (e.g., “Search by image”) independent from PATH 1 text chat flow.
- [ ] 3.2 Implement PATH 2 request handling and error display for invalid/non-PNG uploads.
- [ ] 3.3 Ensure PATH 1 UI interactions and contracts remain unchanged.

## 4. Verification and Rollout Safety

- [ ] 4.1 Add PATH 2 endpoint tests for success, invalid file type, and feature-disabled behavior.
- [ ] 4.2 Add PATH 1 regression checks to verify contract/behavior stability with PATH 2 enabled and disabled.
- [ ] 4.3 Document rollout/rollback procedure based on PATH 2 feature flag and monitoring thresholds.
