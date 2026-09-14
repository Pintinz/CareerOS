"""live discovery engine: source registry, discovery items, runs, change history

Revision ID: c7d1e2f3a4b5
Revises: 45e5467ab49d
Create Date: 2026-09-14 09:00:00.000000

Extends the Phase 9 source registry and discovery queue instead of adding parallel tables, adds
discovery runs, field-level content change history and the AI research cache, and gives jobs,
scholarships and intelligence posts the provenance/source-state columns re-verification needs.

PostgreSQL notes:
- `sourcetype` was created by the jobs migration with 6 values and then reused by the
  content_sources table, whose Python enum had 12 — registry-only values (UNIVERSITY, GOVERNMENT…)
  could not be stored. Every value is now added with ADD VALUE IF NOT EXISTS.
- ALTER TYPE … ADD VALUE runs in an autocommit block: a new value can't be used in the transaction
  that added it, and the data migration below uses the new discovery statuses.
- Enum values cannot be dropped in PostgreSQL, so downgrade leaves the added values in place.
- New enum-like columns are VARCHAR (native_enum=False) so future values need no ALTER TYPE.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c7d1e2f3a4b5'
down_revision: Union[str, None] = '45e5467ab49d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SOURCE_TYPES = [
    'OFFICIAL_CAREER_PAGE', 'OFFICIAL_NEWSROOM', 'INVESTOR_RELATIONS', 'GOVERNMENT', 'REGULATOR', 'UNIVERSITY',
    'SCHOLARSHIP_PROVIDER', 'GREENHOUSE', 'LEVER', 'ASHBY', 'SMARTRECRUITERS', 'WORKDAY', 'SUCCESSFACTORS', 'ORACLE',
    'RSS', 'INDUSTRY_PUBLICATION', 'NEWS_MEDIA', 'AGGREGATOR', 'OTHER',
]
_NEW_ITEM_TYPES = ['INTERNSHIP', 'GRADUATE_PROGRAM', 'FELLOWSHIP']
_NEW_ITEM_STATUSES = ['NEW', 'NEEDS_REVIEW', 'VERIFIED', 'DUPLICATE', 'DRAFT_CREATED', 'PUBLISHED', 'SOURCE_REMOVED', 'ERROR']


def _v(length: int = 40) -> sa.String:
    return sa.String(length)


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == 'sqlite'

    if not is_sqlite:
        with op.get_context().autocommit_block():
            for value in _SOURCE_TYPES:
                op.execute(f"ALTER TYPE sourcetype ADD VALUE IF NOT EXISTS '{value}'")
            op.execute("ALTER TYPE workmode ADD VALUE IF NOT EXISTS 'UNSPECIFIED'")
            op.execute("ALTER TYPE employmenttype ADD VALUE IF NOT EXISTS 'UNSPECIFIED'")
            op.execute("ALTER TYPE fundingtype ADD VALUE IF NOT EXISTS 'UNSPECIFIED'")
            for value in _NEW_ITEM_TYPES:
                op.execute(f"ALTER TYPE discovereditemtype ADD VALUE IF NOT EXISTS '{value}'")
            for value in _NEW_ITEM_STATUSES:
                op.execute(f"ALTER TYPE discovereditemstatus ADD VALUE IF NOT EXISTS '{value}'")

    op.create_table(
        'discovery_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source_id', sa.String(36), nullable=True),
        sa.Column('run_type', _v(), nullable=False),
        sa.Column('trigger', _v(), nullable=False),
        sa.Column('status', _v(), nullable=False),
        sa.Column('requested_by_admin_id', sa.String(36), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('items_found', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_new', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_duplicate', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_invalid', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_removed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('stats_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(['source_id'], ['content_sources.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requested_by_admin_id'], ['admin_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_discovery_runs_source_id', 'discovery_runs', ['source_id'])
    op.create_index('ix_discovery_runs_status', 'discovery_runs', ['status'])
    op.create_index('ix_discovery_runs_queued_at', 'discovery_runs', ['queued_at'])

    op.create_table(
        'research_cache',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'url', 'content_hash', name='uq_research_cache_key'),
    )

    source_columns = [
        sa.Column('domain', sa.String(255), nullable=True),
        sa.Column('region', sa.String(255), nullable=True),
        sa.Column('trust_level', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('discovery_method', _v(), nullable=False, server_default='MANUAL'),
        sa.Column('content_types', sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column('adapter_config_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('polling_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('crawl_interval_minutes', sa.Integer(), nullable=False, server_default='720'),
        sa.Column('auto_publish_allowed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_error_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_code', sa.String(50), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_poll_after', sa.DateTime(timezone=True), nullable=True),
    ]
    with op.batch_alter_table('content_sources', schema=None) as batch_op:
        for column in source_columns:
            batch_op.add_column(column)
        batch_op.create_index('ix_content_sources_domain', ['domain'])

    with op.batch_alter_table('discovered_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('run_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('company_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('canonical_url', sa.String(1024), nullable=True))
        batch_op.add_column(sa.Column('location', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('country', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('deadline', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('extracted_data_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column('evidence_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
        batch_op.add_column(sa.Column('content_hash', sa.String(64), nullable=True))
        batch_op.add_column(sa.Column('discovery_method', _v(), nullable=True))
        batch_op.add_column(sa.Column('verification_status', _v(), nullable=False, server_default='UNVERIFIED'))
        batch_op.add_column(sa.Column('trust_level', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('duplicate_of_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('matched_entity_type', sa.String(30), nullable=True))
        batch_op.add_column(sa.Column('matched_entity_id', sa.String(36), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key('fk_discovered_items_run_id', 'discovery_runs', ['run_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_discovered_items_company_id', 'companies', ['company_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_discovered_items_duplicate_of_id', 'discovered_items', ['duplicate_of_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_discovered_items_run_id', ['run_id'])
        batch_op.create_index('ix_discovered_items_company_id', ['company_id'])
        batch_op.create_index('ix_discovered_items_canonical_url', ['canonical_url'])
        batch_op.create_index('ix_discovered_items_country', ['country'])
        batch_op.create_index('ix_discovered_items_content_hash', ['content_hash'])
        batch_op.create_index('ix_discovered_items_external_id', ['external_id'])
        batch_op.create_index('ix_discovered_items_item_type', ['item_type'])
        batch_op.create_index('ix_discovered_items_matched_entity_id', ['matched_entity_id'])

    if is_sqlite:
        # SQLite stores a (non-native) enum as VARCHAR sized to its longest value at creation time;
        # widen to the new longest values so the declared schema matches the models.
        with op.batch_alter_table('discovered_items', schema=None) as batch_op:
            batch_op.alter_column('item_type', existing_type=sa.String(12), type_=sa.String(16), existing_nullable=False)
            batch_op.alter_column('status', existing_type=sa.String(8), type_=sa.String(14), existing_nullable=False)
        with op.batch_alter_table('jobs', schema=None, naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s"}) as batch_op:
            batch_op.alter_column('work_mode', existing_type=sa.String(7), type_=sa.String(11), existing_nullable=False)
            batch_op.alter_column('employment_type', existing_type=sa.String(10), type_=sa.String(11), existing_nullable=False)

    op.execute("UPDATE discovered_items SET status = 'NEEDS_REVIEW' WHERE status = 'PENDING'")
    op.execute("UPDATE discovered_items SET status = 'DRAFT_CREATED' WHERE status = 'REVIEWED'")

    op.create_table(
        'content_changes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('entity_type', sa.String(30), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('field', sa.String(100), nullable=False),
        sa.Column('old_value_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('new_value_json', sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column('source_id', sa.String(36), nullable=True),
        sa.Column('discovered_item_id', sa.String(36), nullable=True),
        sa.Column('status', _v(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_admin_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['content_sources.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['discovered_item_id'], ['discovered_items.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_admin_id'], ['admin_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_content_changes_entity_type', 'content_changes', ['entity_type'])
    op.create_index('ix_content_changes_entity_id', 'content_changes', ['entity_id'])
    op.create_index('ix_content_changes_discovered_item_id', 'content_changes', ['discovered_item_id'])
    op.create_index('ix_content_changes_status', 'content_changes', ['status'])

    provenance = [
        ('content_source_id', sa.String(36)),
        ('last_verified_at', sa.DateTime(timezone=True)),
    ]

    job_table_kwargs = {}
    if is_sqlite:
        # Same anonymous-FK naming problem the Phase 9.5 migration solved for this table.
        job_table_kwargs = {"naming_convention": {"fk": "fk_%(table_name)s_%(column_0_name)s"}}
    with op.batch_alter_table('jobs', schema=None, **job_table_kwargs) as batch_op:
        batch_op.add_column(sa.Column('opportunity_type', _v(), nullable=False, server_default='JOB'))
        batch_op.add_column(sa.Column('external_job_id', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('requisition_id', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('state_or_region', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('education_requirements', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('experience_requirements', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('program_duration', sa.String(255), nullable=True))
        batch_op.add_column(sa.Column('program_start_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('eligibility_json', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('source_state', _v(), nullable=False, server_default='ACTIVE'))
        for name, type_ in provenance:
            batch_op.add_column(sa.Column(name, type_, nullable=True))
        batch_op.create_foreign_key('fk_jobs_content_source_id', 'content_sources', ['content_source_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_jobs_opportunity_type', ['opportunity_type'])
        batch_op.create_index('ix_jobs_external_job_id', ['external_job_id'])
        batch_op.create_index('ix_jobs_requisition_id', ['requisition_id'])
        batch_op.create_index('ix_jobs_source_state', ['source_state'])
        batch_op.create_index('ix_jobs_content_source_id', ['content_source_id'])

    with op.batch_alter_table('scholarships', schema=None) as batch_op:
        batch_op.add_column(sa.Column('award_type', _v(), nullable=False, server_default='SCHOLARSHIP'))
        batch_op.add_column(sa.Column('opening_date', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('source_state', _v(), nullable=False, server_default='ACTIVE'))
        for name, type_ in provenance:
            batch_op.add_column(sa.Column(name, type_, nullable=True))
        batch_op.create_foreign_key('fk_scholarships_content_source_id', 'content_sources', ['content_source_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_scholarships_award_type', ['award_type'])
        batch_op.create_index('ix_scholarships_source_state', ['source_state'])
        batch_op.create_index('ix_scholarships_content_source_id', ['content_source_id'])

    with op.batch_alter_table('intelligence_posts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('source_name', sa.String(255), nullable=True))
        for name, type_ in provenance:
            batch_op.add_column(sa.Column(name, type_, nullable=True))
        batch_op.create_foreign_key('fk_intelligence_posts_content_source_id', 'content_sources', ['content_source_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('ix_intelligence_posts_content_source_id', ['content_source_id'])


def downgrade() -> None:
    with op.batch_alter_table('intelligence_posts', schema=None) as batch_op:
        batch_op.drop_index('ix_intelligence_posts_content_source_id')
        batch_op.drop_constraint('fk_intelligence_posts_content_source_id', type_='foreignkey')
        for name in ('last_verified_at', 'content_source_id', 'source_name'):
            batch_op.drop_column(name)

    with op.batch_alter_table('scholarships', schema=None) as batch_op:
        for index in ('ix_scholarships_content_source_id', 'ix_scholarships_source_state', 'ix_scholarships_award_type'):
            batch_op.drop_index(index)
        batch_op.drop_constraint('fk_scholarships_content_source_id', type_='foreignkey')
        for name in ('last_verified_at', 'content_source_id', 'source_state', 'opening_date', 'award_type'):
            batch_op.drop_column(name)

    with op.batch_alter_table('jobs', schema=None) as batch_op:
        for index in ('ix_jobs_content_source_id', 'ix_jobs_source_state', 'ix_jobs_requisition_id', 'ix_jobs_external_job_id', 'ix_jobs_opportunity_type'):
            batch_op.drop_index(index)
        batch_op.drop_constraint('fk_jobs_content_source_id', type_='foreignkey')
        for name in (
            'last_verified_at', 'content_source_id', 'source_state', 'eligibility_json', 'program_start_date',
            'program_duration', 'experience_requirements', 'education_requirements', 'state_or_region',
            'requisition_id', 'external_job_id', 'opportunity_type',
        ):
            batch_op.drop_column(name)

    op.drop_table('content_changes')

    op.execute("UPDATE discovered_items SET status = 'PENDING' WHERE status IN ('NEW', 'NEEDS_REVIEW', 'VERIFIED', 'DUPLICATE', 'ERROR')")
    op.execute("UPDATE discovered_items SET status = 'REVIEWED' WHERE status IN ('DRAFT_CREATED', 'PUBLISHED')")
    op.execute("UPDATE discovered_items SET status = 'IGNORED' WHERE status = 'SOURCE_REMOVED'")
    op.execute("UPDATE discovered_items SET item_type = 'JOB' WHERE item_type IN ('INTERNSHIP', 'GRADUATE_PROGRAM')")
    op.execute("UPDATE discovered_items SET item_type = 'SCHOLARSHIP' WHERE item_type = 'FELLOWSHIP'")

    with op.batch_alter_table('discovered_items', schema=None) as batch_op:
        for index in (
            'ix_discovered_items_matched_entity_id', 'ix_discovered_items_item_type', 'ix_discovered_items_external_id',
            'ix_discovered_items_content_hash', 'ix_discovered_items_country', 'ix_discovered_items_canonical_url',
            'ix_discovered_items_company_id', 'ix_discovered_items_run_id',
        ):
            batch_op.drop_index(index)
        for fk in ('fk_discovered_items_duplicate_of_id', 'fk_discovered_items_company_id', 'fk_discovered_items_run_id'):
            batch_op.drop_constraint(fk, type_='foreignkey')
        for name in (
            'last_verified_at', 'last_seen_at', 'matched_entity_id', 'matched_entity_type', 'duplicate_of_id',
            'confidence', 'trust_level', 'verification_status', 'discovery_method', 'content_hash', 'evidence_json',
            'extracted_data_json', 'deadline', 'published_at', 'country', 'location', 'canonical_url', 'company_id', 'run_id',
        ):
            batch_op.drop_column(name)

    with op.batch_alter_table('content_sources', schema=None) as batch_op:
        batch_op.drop_index('ix_content_sources_domain')
        for name in (
            'next_poll_after', 'consecutive_failures', 'last_error_code', 'last_error_at', 'auto_publish_allowed',
            'crawl_interval_minutes', 'polling_enabled', 'adapter_config_json', 'content_types', 'discovery_method',
            'trust_level', 'region', 'domain',
        ):
            batch_op.drop_column(name)

    op.drop_table('research_cache')
    op.drop_index('ix_discovery_runs_queued_at', table_name='discovery_runs')
    op.drop_index('ix_discovery_runs_status', table_name='discovery_runs')
    op.drop_index('ix_discovery_runs_source_id', table_name='discovery_runs')
    op.drop_table('discovery_runs')
