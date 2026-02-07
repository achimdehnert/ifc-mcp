# 🔌 IFC MCP + cad_hub Integration Guide

## 🎯 Architecture Overview

```
┌────────────────────────────────────────────┐
│  IFC MCP Backend (Single Source of Truth)  │
│  ────────────────────────────────────── │
│  Domain Layer:                             │
│    - Project, Storey, Space                │
│    - Repositories (Interfaces)             │
│  ────────────────────────────────────── │
│  Application Services:                     │
│    - ImportService                         │
│    - ScheduleService                       │
│    - ExProtectionService (ATEX)            │
│    - DIN277Service (German Standard)       │
│    - WoFlVService (German Standard)        │
│    - GAEBService (German Standard)         │
│  ────────────────────────────────────── │
│  Presentation Layer:                       │
│    - FastAPI REST API (Port 8001)          │
│    - MCP Tools (stdio)                     │
└────────────────────────────────────────────┘
                ↑
                │ HTTP/REST
                ↓
┌────────────────────────────────────────────┐
│  cad_hub Frontend (Pure UI Layer)          │
│  ────────────────────────────────────── │
│  - Django Templates + HTMX                 │
│  - Views (NO Business Logic!)              │
│  - IfcMcpClient (HTTP Client)              │
│  - UI Cache Models                         │
└────────────────────────────────────────────┘
```

## 🚀 Quick Start

### 1. Start IFC MCP Backend:
```bash
cd ifc-mcp

# Install dependencies
pip install -e .

# Start FastAPI server
python -m uvicorn ifc_mcp.presentation.api.app:app --reload --port 8001
```

### 2. Start cad_hub Frontend:
```bash
cd bfagent

# Configure IFC MCP URL (in settings.py or .env)
IFC_MCP_URL=http://localhost:8001

# Start Django server
python manage.py runserver
```

## 📡 API Endpoints

### Projects:
- `POST /api/v1/projects/import` - Upload & parse IFC file
- `GET /api/v1/projects` - List all projects
- `GET /api/v1/projects/{id}` - Project details
- `DELETE /api/v1/projects/{id}` - Delete project

### German Standards:
- `POST /api/v1/din277/calculate` - DIN 277:2021 area calculation
- `POST /api/v1/woflv/calculate` - WoFlV residential area
- `POST /api/v1/gaeb/generate` - GAEB bill of quantities (XML/Excel)

### Schedules:
- `POST /api/v1/projects/{id}/schedules/windows` - Window schedule
- `POST /api/v1/projects/{id}/schedules/doors` - Door schedule
- `POST /api/v1/projects/{id}/schedules/walls` - Wall schedule

### Ex-Protection (ATEX):
- `GET /api/v1/projects/{id}/ex-zones` - Analyze explosion zones
- `GET /api/v1/projects/{id}/fire-rating` - Fire rating analysis
- `GET /api/v1/projects/{id}/room-volumes` - Room volumes

## 🎯 Naming Conventions

### Services (IFC MCP):
```python
# ✅ CORRECT:
class ImportService:
class ScheduleService:
class DIN277Service:
class WoFlVService:
class GAEBService:
```

### Domain Entities:
```python
# ✅ CORRECT (IFC-Standard):
Project         # IfcProject
Storey          # IfcBuildingStorey
Space           # IfcSpace
```

## 📦 Deployment

### Docker Compose:
```yaml
version: "3.8"

services:
  ifc_mcp:
    build: ./ifc-mcp
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: postgresql+asyncpg://...
  
  cad_hub:
    build: ./bfagent
    ports:
      - "8000:8000"
    environment:
      IFC_MCP_URL: http://ifc_mcp:8001
    depends_on:
      - ifc_mcp
```

---

**Status**: ✅ PRODUCTION READY
**Version**: 1.0.0
