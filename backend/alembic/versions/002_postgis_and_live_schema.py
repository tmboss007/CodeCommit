"""Align Alembic 001 with the live ORM and PostGIS extras.

Revision ID: 002
Revises: 001
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("ALTER TABLE zones ALTER COLUMN location DROP NOT NULL")

    op.execute("ALTER TABLE zones ADD COLUMN IF NOT EXISTS priority_breakdown JSON")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS duplicate_status VARCHAR DEFAULT 'NEW'")
    op.execute("ALTER TABLE allocations ADD COLUMN IF NOT EXISTS from_zone_id VARCHAR")
    op.execute("ALTER TABLE allocations ADD COLUMN IF NOT EXISTS approved_by VARCHAR")
    op.execute("ALTER TABLE coordination_tasks ADD COLUMN IF NOT EXISTS plan_id VARCHAR")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id VARCHAR PRIMARY KEY,
            status VARCHAR NOT NULL DEFAULT 'pending_approval',
            trigger VARCHAR,
            previous_plan_id VARCHAR,
            created_at TIMESTAMP,
            approved_at TIMESTAMP,
            rejected_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_state (
            id VARCHAR PRIMARY KEY,
            last_plan_id VARCHAR,
            last_plan_status VARCHAR DEFAULT 'none',
            last_plan_trigger VARCHAR,
            active_plan_id VARCHAR,
            last_snapshot JSON,
            last_delta JSON,
            last_unmet JSON,
            last_explanation TEXT,
            blocked_routes JSON,
            data_mode VARCHAR DEFAULT 'SIMULATION',
            updated_at TIMESTAMP
        )
        """
    )

    op.execute("ALTER TABLE zones ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)")
    op.execute("ALTER TABLE resources ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)")
    op.execute("ALTER TABLE incidents ADD COLUMN IF NOT EXISTS location geometry(Point, 4326)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_zone_id ON incidents (zone_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_timestamp ON incidents (timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_status ON incidents (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resources_status ON resources (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resources_agency_id ON resources (agency_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_allocations_plan_id ON allocations (plan_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_coordination_tasks_plan_id ON coordination_tasks (plan_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_zones_location ON zones USING GIST (location)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_resources_location ON resources USING GIST (location)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_incidents_location ON incidents USING GIST (location)")

    op.execute(
        "UPDATE zones SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL"
    )
    op.execute(
        "UPDATE resources SET location = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326) "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL AND location IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app_state")
    op.execute("DROP TABLE IF EXISTS plans")
