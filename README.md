# IFC MCP Server

An MCP (Model Context Protocol) server for processing IFC (Industry Foundation Classes) files with PostgreSQL backend.

## Features

### Construction Use Cases
- **Window Schedule** - List of all windows with dimensions, U-values, fire ratings
- **Door Schedule** - Door list with fire/acoustic ratings
- **Wall Schedule** - Wall list with materials, load-bearing status
- **Drywall Schedule** - Filtered list of partition walls (Trockenbau)
- **Room Schedule** - Room book (Raumbuch) with areas, volumes, finishes

### Explosion Protection (ATEX)
- **Ex-Zone Analysis** - Identify hazardous areas (Zone 0-2, Zone 20-22)
- **Fire Rating Report** - Fire protection classification of elements
- **Room Volume Analysis** - Volumes for ventilation calculations
- **Hazardous Area Check** - Safety issue identification

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Docker (optional)

### Installation

```bash
git clone https://github.com/achimdehnert/ifc-mcp.git
cd ifc-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### Running the Server

```bash
python -m ifc_mcp
```

## License

MIT
