## Why

PATH 1 (text-to-image conversational search) is currently stable and already deployed.  
The project now needs PATH 2 (image-to-image search), but it must be introduced without changing PATH 1 behavior or reliability.

## What Changes

- Add a dedicated PATH 2 image-query flow with a separate API contract and execution path.
- Add strict upload validation for PATH 2 query images (PNG policy) with explicit error responses.
- Add an isolated PATH 2 retrieval module that does not modify or route through PATH 1 `search()` logic.
- Add feature gating so PATH 2 can be enabled/disabled independently of PATH 1.
- Add regression coverage and operational checks to prove PATH 1 behavior is unchanged.

## Capabilities

### New Capabilities
- `path2-image-query`: Support uploading a query garment image and retrieving visually similar products through a dedicated PATH 2 endpoint.
- `path1-isolation-guard`: Guarantee PATH 2 rollout cannot alter PATH 1 APIs, ranking behavior, or error handling.

### Modified Capabilities
- None.

## Impact

- Affected systems: FastAPI API surface, retrieval layer, and optional Clothie UI entry for PATH 2.
- New artifacts: PATH 2-specific endpoint(s), PATH 2 retrieval module, validation policy, and regression tests.
- Operational impact: Additional inference workload for image-query requests only; PATH 1 runtime path remains unchanged.
- Deployment impact: New feature flag for PATH 2 enablement and controlled rollout.
