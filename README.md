# LobeChat Local Stack

Self-hosted LobeChat with PostgreSQL, Casdoor authentication, and MinIO storage.

## Quick Start

```bash
docker compose up -d
```

## Architecture

See [docs/architecture.drawio](docs/architecture.drawio) for visual diagram.

```
User --> LobeChat (:47000)
              |
              +--> Casdoor (:47002)  --> PostgreSQL (casdoor db)
              |
              +--> MinIO (:47005)    --> ./data/minio
              |
              +--> PostgreSQL        --> ./data/postgres
                   (lobechat db)
```

## Services

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| LobeChat | lobe-chat | 47000 | Main application |
| Casdoor | casdoor | 47002 | SSO authentication |
| MinIO S3 | minio | 47005 | Object storage API |
| MinIO Console | minio | 47006 | Storage admin UI |
| PostgreSQL | shared-postgres | - | Database (internal) |

## Access

| Service | URL |
|---------|-----|
| LobeChat | http://localhost:47000 |
| Casdoor Admin | http://localhost:47002 |
| MinIO Console | http://localhost:47006 |

## Credentials

| Service | Username | Password |
|---------|----------|----------|
| LobeChat | user | pswd123 |
| MinIO | minioadmin | minioadmin |

## Commands

```bash
docker compose up -d          # Start
docker compose down           # Stop
docker compose logs -f        # All logs
docker compose logs -f lobe-chat  # LobeChat logs
docker compose restart lobe-chat  # Restart service
```

## Project Structure

```
.
├── docker-compose.yml     # Stack definition
├── .env                   # Environment variables
├── config/
│   ├── casdoor-app.conf   # Casdoor server config
│   ├── init_data.json     # Casdoor initial data
│   ├── init-postgres.sql  # Database init script
│   └── esade.pem          # AWS SSH key (future use)
├── data/
│   ├── postgres/          # PostgreSQL data
│   └── minio/             # Uploaded files
└── docs/
    └── architecture.drawio  # Architecture diagram
```

## Configuration

Edit `.env` for:
- `AUTH_CASDOOR_*` - SSO settings
- `S3_*` - MinIO storage
- `POSTGRES_PASSWORD` - Database password
- `KEY_VAULTS_SECRET` - API key encryption



## DevOps Homework  2
This change was made to trigger the CI pipeline.
