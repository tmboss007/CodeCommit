"""initial migration

Revision ID: 001
Create Date: 2026-09-11

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Enable PostGIS
    op.execute('CREATE EXTENSION IF NOT EXISTS postgis')

    # Zones
    op.create_table(
        'zones',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('location', Geometry('POINT', srid=4326), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('population', sa.Integer(), default=0),
        sa.Column('vulnerable_population', sa.Integer(), default=0),
        sa.Column('severity', sa.Float(), default=0),
        sa.Column('priority_score', sa.Float(), default=0),
        sa.Column('status', sa.String(), default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Agencies
    op.create_table(
        'agencies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String()),
        sa.Column('contact', sa.String()),
        sa.Column('capabilities', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Incidents
    op.create_table(
        'incidents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('zone_id', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('source_reference', sa.String()),
        sa.Column('report_text', sa.Text(), nullable=False),
        sa.Column('incident_type', sa.String()),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('location', Geometry('POINT', srid=4326)),
        sa.Column('affected_population', sa.Integer()),
        sa.Column('vulnerable_population', sa.Integer()),
        sa.Column('confidence', sa.Float()),
        sa.Column('status', sa.String(), default='active'),
        sa.Column('duplicate_group_id', sa.String()),
        sa.Column('analysis_result', sa.JSON()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Needs
    op.create_table(
        'needs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('incident_id', sa.String()),
        sa.Column('zone_id', sa.String()),
        sa.Column('resource_type', sa.String(), nullable=False),
        sa.Column('quantity_required', sa.Float(), nullable=False),
        sa.Column('quantity_fulfilled', sa.Float(), default=0),
        sa.Column('quantity_remaining', sa.Float()),
        sa.Column('urgency', sa.Float(), default=0.5),
        sa.Column('unit', sa.String()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.id']),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Resources
    op.create_table(
        'resources',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('agency_id', sa.String(), nullable=False),
        sa.Column('location', Geometry('POINT', srid=4326)),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('quantity', sa.Float()),
        sa.Column('unit', sa.String()),
        sa.Column('capacity', sa.Float()),
        sa.Column('capabilities', sa.JSON()),
        sa.Column('status', sa.String(), default='available'),
        sa.Column('current_zone_id', sa.String()),
        sa.Column('available_at', sa.DateTime()),
        sa.Column('eta_minutes', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id']),
        sa.ForeignKeyConstraint(['current_zone_id'], ['zones.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Allocations
    op.create_table(
        'allocations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=False),
        sa.Column('zone_id', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float()),
        sa.Column('priority', sa.Float()),
        sa.Column('eta_minutes', sa.Integer()),
        sa.Column('reason', sa.Text()),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('plan_id', sa.String()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('approved_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['resource_id'], ['resources.id']),
        sa.ForeignKeyConstraint(['zone_id'], ['zones.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Coordination Tasks
    op.create_table(
        'coordination_tasks',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agency_id', sa.String(), nullable=False),
        sa.Column('allocation_id', sa.String()),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), default='pending'),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('approved_at', sa.DateTime()),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id']),
        sa.ForeignKeyConstraint(['allocation_id'], ['allocations.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Audit Events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('actor', sa.String()),
        sa.Column('agent', sa.String()),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('input_reference', sa.String()),
        sa.Column('previous_state', sa.JSON()),
        sa.Column('new_state', sa.JSON()),
        sa.Column('reason', sa.Text()),
        sa.Column('correlation_id', sa.String()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_events_timestamp', 'audit_events', ['timestamp'])
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])
    op.create_index('ix_audit_events_correlation_id', 'audit_events', ['correlation_id'])

    # Replanning Events
    op.create_table(
        'replanning_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('trigger', sa.String(), nullable=False),
        sa.Column('old_plan_id', sa.String()),
        sa.Column('new_plan_id', sa.String()),
        sa.Column('changed_zones', sa.JSON()),
        sa.Column('changed_resources', sa.JSON()),
        sa.Column('delta', sa.JSON()),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('correlation_id', sa.String()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('replanning_events')
    op.drop_index('ix_audit_events_correlation_id')
    op.drop_index('ix_audit_events_event_type')
    op.drop_index('ix_audit_events_timestamp')
    op.drop_table('audit_events')
    op.drop_table('coordination_tasks')
    op.drop_table('allocations')
    op.drop_table('resources')
    op.drop_table('needs')
    op.drop_table('incidents')
    op.drop_table('agencies')
    op.drop_table('zones')
