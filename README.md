# IFC MCP Server

An MCP (Model Context Protocol) server for processing IFC (Industry Foundation Classes) files with PostgreSQL backend.

## Features

### Construction Use Cases
- **Window Schedule** - List of all windows with dimensions, U-values, fire ratings
- **Door Schedule** - Door list with fire/acoustic ratings
- **Wall Schedule** - Wall list with materials, load-bearing status
- **Drywall Schedule** - Filtered list of partition walls (Trockenbau)
- **Room Schedule** - Room book (Raumbuch) with areas, volumes, finishes

### Fire Safety & Plans
- **Fire Escape Plans** - DIN ISO 23601 compliant escape plans (SVG)
- **Fire Compartment Maps** - Color-coded fire rating visualization
- **Fire Rating Reports** - Element fire classification analysis

### Analysis & Compliance
- **Material Takeoff** - Quantity takeoffs per DIN 276/VOB standards
- **Model Quality Check** - Geometry, properties, relationships, naming, consistency
- **Accessibility Check** - DIN 18040-1/2 compliance
- **DIN 277 Areas** - Area calculations per DIN 277:2021
- **WoFlV Areas** - German residential area regulation
- **GAEB Export** - Construction tender documents (XML + Excel)

### Explosion Protection (ATEX)
- **Ex-Zone Analysis** - Identify hazardous areas (Zone 0-2, Zone 20-22)
- **Room Volume Analysis** - Volumes for ventilation calculations
- **Hazardous Area Check** - Safety issue identification

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│                   (MCP Server + Tools)                       │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│               (Services, Queries, Commands)                  │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│        (Entities, Value Objects, Repository Interfaces)      │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│         (SQLAlchemy, PostgreSQL, IfcOpenShell)              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Docker (optional)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd ifc_mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env
# Edit .env with your database credentials
```

### Database Setup

```bash
# Start PostgreSQL with Docker
docker-compose up -d db

# Run migrations
alembic upgrade head
```

### Running the Server

```bash
# Run MCP server
python -m ifc_mcp

# Or use the CLI
ifc-mcp
```

## MCP Tools

### Project Management

| Tool | Description |
|------|-------------|
| `ifc_import_file` | Import an IFC file into the database |
| `ifc_list_projects` | List all imported projects |
| `ifc_get_project` | Get project details with storeys |
| `ifc_delete_project` | Delete a project |

### Schedules

| Tool | Description |
|------|-------------|
| `ifc_window_schedule` | Generate window list |
| `ifc_door_schedule` | Generate door list |
| `ifc_wall_schedule` | Generate wall list |
| `ifc_drywall_schedule` | Generate drywall list |
| `ifc_room_schedule` | Generate room book |

### Fire Safety

| Tool | Description |
|------|-------------|
| `ifc_fire_escape_plan` | DIN ISO 23601 escape plan (SVG) |
| `ifc_fire_compartment_map` | Fire compartment visualization |
| `ifc_floor_plan_svg` | General floor plan (SVG) |

### Analysis

| Tool | Description |
|------|-------------|
| `ifc_material_takeoff` | DIN 276 material takeoff |
| `ifc_model_check` | Model quality checks |
| `ifc_accessibility_check` | DIN 18040 accessibility |

### Explosion Protection

| Tool | Description |
|------|-------------|
| `ifc_ex_zone_analysis` | Analyze Ex-Zones (ATEX) |
| `ifc_fire_rating_report` | Fire rating report |
| `ifc_room_volume_analysis` | Room volumes |
| `ifc_hazardous_areas` | Safety check |

### Export

| Tool | Description |
|------|-------------|
| `ifc_export_all_excel` | Export all schedules to Excel |
| `ifc_export_window_excel` | Export window schedule |
| `ifc_export_door_excel` | Export door schedule |
| `ifc_export_room_excel` | Export room schedule |
| `ifc_export_ex_protection_excel` | Export Ex-Protection report |

## Development

### Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=ifc_mcp

# Only unit tests
pytest -m unit

# Only integration tests (requires database)
pytest -m integration
```

### Code Quality

```bash
# Format code
ruff format src tests

# Lint
ruff check src tests

# Type checking
mypy src
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Configuration

Environment variables (prefix `IFC_MCP_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection URL |
| `DATABASE_POOL_SIZE` | `10` | Connection pool size |
| `LOG_LEVEL` | `INFO` | Logging level |
| `LOG_FORMAT` | `json` | Log format (json/console) |
| `IFC_IMPORT_BATCH_SIZE` | `500` | Batch size for imports |
| `DEFAULT_PAGE_SIZE` | `50` | Default pagination size |

## Project Structure

```
ifc_mcp/
├── src/ifc_mcp/
│   ├── presentation/     # MCP Server, Tools
│   │   ├── server.py
│   │   └── tools/
│   ├── application/      # Services, Use Cases
│   │   └── services/
│   ├── domain/           # Core Business Logic
│   │   ├── models/
│   │   ├── value_objects/
│   │   └── repositories/
│   ├── infrastructure/   # External Integrations
│   │   ├── database/
│   │   ├── repositories/
│   │   └── ifc/
│   └── shared/           # Config, Logging
├── tests/
├── alembic/              # Database Migrations
├── docker-compose.yml
└── pyproject.toml
```

## License

MIT
