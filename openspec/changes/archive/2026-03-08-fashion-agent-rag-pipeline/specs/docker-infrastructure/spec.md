## ADDED Requirements

### Requirement: Docker Compose stack
The system SHALL provide a `docker-compose.yml` defining 4 services: `postgres`, `qdrant`, `fashion-api`, and `cloudflared`, all connected via an internal bridge network.

#### Scenario: Stack startup
- **WHEN** user runs `docker compose up -d`
- **THEN** all 4 containers start successfully and reach healthy state within 60 seconds

#### Scenario: PostgreSQL persistence
- **WHEN** Docker containers are stopped and restarted
- **THEN** all PostgreSQL data persists via named volume `pgdata`

#### Scenario: Qdrant persistence
- **WHEN** Docker containers are stopped and restarted
- **THEN** all Qdrant vector data persists via named volume `qdrant_data`

### Requirement: Network isolation
PostgreSQL and Qdrant SHALL NOT expose ports to the host machine. Only the internal Docker network SHALL be used for inter-service communication.

#### Scenario: Port isolation
- **WHEN** user runs `docker compose up -d`
- **THEN** ports 5432 (postgres) and 6333 (qdrant) are NOT accessible from the host, only from within the Docker network

### Requirement: Environment configuration
The system SHALL use a `.env` file for secrets (PG_PASSWORD, GEMINI_API_KEY, CF_TUNNEL_TOKEN) and provide a `.env.example` template.

#### Scenario: Missing env file
- **WHEN** user runs `docker compose up -d` without `.env` file
- **THEN** Docker Compose fails with a clear error indicating missing environment variables

### Requirement: Cloudflare Tunnel routing
The `cloudflared` container SHALL create an outbound tunnel to Cloudflare edge, routing HTTPS traffic from the configured domain to `fashion-api:8000`.

#### Scenario: Public API access
- **WHEN** user accesses `https://fashion-agent.domain.com/api/health`
- **THEN** the request routes through Cloudflare Tunnel to the fashion-api container and returns a 200 OK response

### Requirement: Health checks
PostgreSQL container SHALL have a health check using `pg_isready`. The `fashion-api` container SHALL depend on PostgreSQL's healthy state before starting.

#### Scenario: Dependency ordering
- **WHEN** Docker Compose starts services
- **THEN** `fashion-api` waits for PostgreSQL health check to pass before starting
