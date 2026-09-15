"""career source integration: registry readiness, sync health, draft fast-path, removal confirmation

Revision ID: d8e2f4a6b7c9
Revises: c7d1e2f3a4b5
Create Date: 2026-09-15 12:00:00.000000

Extends the existing source registry for direct company career feeds (CAREER_SOURCE_INTEGRATION.md):
- content_sources: job_search_url, ats_provider, readiness (+ note), auto_create_draft,
  last_http_status, items_last_found
- jobs.job_function (department / job family as the employer names it)
- discovered_items.missing_runs and jobs.source_missing_runs: consecutive complete syncs in which a
  listing was absent, so removal needs configurable confirmation instead of one missed fetch
- new opportunity types APPRENTICESHIP and TRAINEE_PROGRAM. jobs.opportunity_type and
  jobs.source_state (new POSSIBLY_REMOVED) are VARCHAR and need no change; discovereditemtype is a
  native PostgreSQL enum, so values are added in an autocommit block (they cannot be dropped on
  downgrade). Both new names fit the existing SQLite VARCHAR(16).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd8e2f4a6b7c9'
down_revision: Union[str, None] = 'c7d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        with op.get_context().autocommit_block():
            for value in ('APPRENTICESHIP', 'TRAINEE_PROGRAM'):
                op.execute(f"ALTER TYPE discovereditemtype ADD VALUE IF NOT EXISTS '{value}'")

    with op.batch_alter_table('content_sources', schema=None) as batch_op:
        batch_op.add_column(sa.Column('job_search_url', sa.String(1024), nullable=True))
        batch_op.add_column(sa.Column('ats_provider', sa.String(40), nullable=True))
        batch_op.add_column(sa.Column('readiness', sa.String(40), nullable=False, server_default='UNVERIFIED'))
        batch_op.add_column(sa.Column('readiness_note', sa.String(500), nullable=True))
        batch_op.add_column(sa.Column('auto_create_draft', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('last_http_status', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('items_last_found', sa.Integer(), nullable=True))

    with op.batch_alter_table('discovered_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('missing_runs', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_missing_runs', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('job_function', sa.String(255), nullable=True))


def downgrade() -> None:
    op.execute("UPDATE jobs SET source_state = 'ACTIVE' WHERE source_state = 'POSSIBLY_REMOVED'")
    op.execute("UPDATE jobs SET opportunity_type = 'GRADUATE_PROGRAM' WHERE opportunity_type = 'TRAINEE_PROGRAM'")
    op.execute("UPDATE jobs SET opportunity_type = 'INTERNSHIP' WHERE opportunity_type = 'APPRENTICESHIP'")
    op.execute("UPDATE discovered_items SET item_type = 'GRADUATE_PROGRAM' WHERE item_type = 'TRAINEE_PROGRAM'")
    op.execute("UPDATE discovered_items SET item_type = 'INTERNSHIP' WHERE item_type = 'APPRENTICESHIP'")
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_column('job_function')
        batch_op.drop_column('source_missing_runs')
    with op.batch_alter_table('discovered_items', schema=None) as batch_op:
        batch_op.drop_column('missing_runs')
    with op.batch_alter_table('content_sources', schema=None) as batch_op:
        for column in ('items_last_found', 'last_http_status', 'auto_create_draft', 'readiness_note', 'readiness', 'ats_provider', 'job_search_url'):
            batch_op.drop_column(column)
