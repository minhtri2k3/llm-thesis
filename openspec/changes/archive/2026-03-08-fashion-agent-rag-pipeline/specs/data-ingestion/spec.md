## MODIFIED Requirements

### Requirement: Database connection
The system SHALL connect to PostgreSQL via Docker internal network hostname `postgres` instead of Google Cloud SQL proxy. All GCP-specific code (gcloud auth, ADC token, cloud-sql-proxy socket) SHALL be removed.

#### Scenario: Docker PostgreSQL connection
- **WHEN** processing_data.py connects to database
- **THEN** connection uses PGHOST=postgres (Docker service name), PGPORT=5432, and standard psycopg2 connection without any GCP proxy

#### Scenario: Doctor command simplified
- **WHEN** user runs `python processing_data.py doctor`
- **THEN** system checks PostgreSQL connectivity only (no gcloud, no ADC, no proxy socket checks)

## REMOVED Requirements

### Requirement: Google Cloud SQL proxy support
**Reason**: Migrating from GCP Cloud SQL to Docker local PostgreSQL for self-hosting
**Migration**: Use Docker Compose PostgreSQL at `postgres:5432` instead of cloud-sql-proxy unix socket

### Requirement: GCP authentication checks
**Reason**: No longer using GCP services for database
**Migration**: Remove `check_gcloud_exists()`, `check_adc_token()`, `check_proxy_socket()` from doctor command. Remove `GCP_PROJECT_ID` and `INSTANCE_CONNECTION_NAME` env vars.
