# NEXUS-R Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ with PostGIS extension
- Redis 6+

## Backend Setup

### 1. Install PostgreSQL and PostGIS

**Windows:**
```bash
# Download PostgreSQL installer from postgresql.org
# During installation, ensure PostGIS is selected in Stack Builder
```

**Linux:**
```bash
sudo apt-get update
sudo apt-get install postgresql-14 postgresql-14-postgis-3
```

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE nexus_r;

# Connect to the database
\c nexus_r

# Enable PostGIS
CREATE EXTENSION postgis;

# Exit
\q
```

### 3. Backend Installation

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### 4. Configure .env

```bash
# Required settings
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nexus_r
REDIS_URL=redis://localhost:6379/0

# LLM API (at least one required)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

LLM_PROVIDER=openai  # or anthropic
LLM_MODEL=gpt-4-turbo-preview  # or claude-3-opus-20240229
```

### 5. Run Migrations

```bash
# Run database migrations
alembic upgrade head

# Seed demo data
python scripts/seed_demo_data.py
```

### 6. Start Backend

```bash
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000
API docs at: http://localhost:8000/docs

## Frontend Setup

### 1. Install Dependencies

```bash
cd frontend
npm install
```

### 2. Configure Environment

```bash
cp .env.local.example .env.local
# Edit .env.local if needed
```

Default:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Start Frontend

```bash
npm run dev
```

Frontend runs at: http://localhost:3000

## Verify Installation

1. Open http://localhost:3000
2. You should see the Command Center dashboard
3. Verify 5 zones are displayed
4. Check that resources are loaded

## Demo Scenario

### Load Initial State

The seed script creates:
- 5 zones (A, B, C, D, E)
- 5 agencies (NDRF, Fire, District, NGO, Medical)
- 12 resources (rescue teams, medical, water, food, shelter)

### Submit Test Incident

1. Navigate to Incidents page
2. Click "Report Incident"
3. Paste:
```
Severe flooding in Zone A. Water level rising rapidly.
Approximately 2000 people affected. Two rescue routes blocked.
Immediate evacuation support required.
```
4. Submit

### Watch Agent Pipeline

The system will:
1. ✅ Situation Agent extracts information
2. ✅ Needs Agent calculates requirements
3. ✅ Priority Agent updates zone score
4. ✅ Duplicate Agent checks for overlaps
5. ✅ Optimization generates allocation
6. ✅ Coordination Agent creates tasks
7. ✅ Audit log records all actions

### Trigger Re-planning

1. Submit another urgent report for same zone
2. System detects priority change
3. Re-planning automatically triggers
4. View allocation delta (before/after)
5. Approve revised plan

## Troubleshooting

### Database Connection Fails

```bash
# Check PostgreSQL is running
# Windows: Services -> PostgreSQL
# Linux: sudo systemctl status postgresql

# Test connection
psql -U postgres -d nexus_r -c "SELECT version();"
```

### PostGIS Extension Error

```bash
# Manually enable PostGIS
psql -U postgres -d nexus_r
CREATE EXTENSION IF NOT EXISTS postgis;
```

### LLM API Errors

- Verify API key is correct
- Check internet connection
- Ensure API credits/quota available
- Try switching provider in .env

### Frontend Can't Connect

- Verify backend is running on port 8000
- Check NEXT_PUBLIC_API_URL in .env.local
- Disable browser CORS extensions temporarily

### Redis Connection Issues

```bash
# Windows: Download Redis from GitHub releases
# Linux: sudo apt-get install redis-server

# Start Redis
redis-server
```

## Production Notes

This is a hackathon MVP. For production:

1. Use environment-specific secrets
2. Enable authentication
3. Configure HTTPS
4. Set up proper logging
5. Use production database
6. Deploy with proper CORS settings
7. Add rate limiting
8. Implement proper error handling
9. Add monitoring/alerting
10. Use external routing API

## Support

For issues, check:
- Backend logs in terminal
- Frontend console (F12)
- Database connection
- API endpoint responses (/docs)
