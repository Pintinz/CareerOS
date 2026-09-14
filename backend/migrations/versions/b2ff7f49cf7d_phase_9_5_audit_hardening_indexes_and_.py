"""phase 9.5 audit hardening indexes and job company fk restrict

Revision ID: b2ff7f49cf7d
Revises: 2146a3e4995f
Create Date: 2026-09-13 13:46:52.788775

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2ff7f49cf7d'
down_revision: Union[str, None] = '2146a3e4995f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JOB_INDEXES = [
    ('ix_jobs_application_deadline', 'application_deadline'),
    ('ix_jobs_expires_at', 'expires_at'),
    ('ix_jobs_is_active', 'is_active'),
    ('ix_jobs_published_at', 'published_at'),
    ('ix_jobs_status', 'status'),
]


def _existing_company_fk_name(bind) -> str:
    for fk in sa.inspect(bind).get_foreign_keys('jobs'):
        if fk['constrained_columns'] == ['company_id']:
            return fk['name']
    raise RuntimeError("jobs.company_id foreign key not found")


def upgrade() -> None:
    op.create_index(op.f('ix_applications_current_stage'), 'applications', ['current_stage'], unique=False)
    op.create_index(op.f('ix_discovered_items_status'), 'discovered_items', ['status'], unique=False)
    op.create_index(op.f('ix_recruitment_email_events_status'), 'recruitment_email_events', ['status'], unique=False)

    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        # Phase 11 Postgres validation found the original batch rebuild below cannot work on a real
        # database: recreate='always' copies and drops `jobs`, which Postgres refuses because five
        # other tables hold foreign keys into it, and Postgres auto-named the original constraint
        # `jobs_company_id_fkey`, not `fk_jobs_company_id`. Real databases support ALTER TABLE
        # directly, so no rebuild is needed — look the constraint name up rather than assuming it.
        for name, column in _JOB_INDEXES:
            op.create_index(name, 'jobs', [column], unique=False)
        op.drop_constraint(_existing_company_fk_name(bind), 'jobs', type_='foreignkey')
        op.create_foreign_key(
            'fk_jobs_company_id', 'jobs', 'companies', ['company_id'], ['id'], ondelete='RESTRICT'
        )
        return

    # SQLite has no ALTER TABLE ... ADD/DROP CONSTRAINT, so the table must be rebuilt. The original
    # jobs.company_id foreign key is anonymous (defined inline in the very first migration); a
    # `naming_convention` gives the reflected FK a deterministic name so it can actually be dropped,
    # not just shadowed by a second FK on the same column.
    naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table('jobs', schema=None, recreate='always', naming_convention=naming_convention) as batch_op:
        for name, column in _JOB_INDEXES:
            batch_op.create_index(name, [column], unique=False)
        batch_op.drop_constraint('fk_jobs_company_id', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_jobs_company_id', 'companies', ['company_id'], ['id'], ondelete='RESTRICT'
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_recruitment_email_events_status'), table_name='recruitment_email_events')

    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.drop_constraint('fk_jobs_company_id', 'jobs', type_='foreignkey')
        op.create_foreign_key(
            'jobs_company_id_fkey', 'jobs', 'companies', ['company_id'], ['id'], ondelete='CASCADE'
        )
        for name, _ in reversed(_JOB_INDEXES):
            op.drop_index(name, table_name='jobs')
    else:
        naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s"}
        with op.batch_alter_table('jobs', schema=None, recreate='always', naming_convention=naming_convention) as batch_op:
            batch_op.drop_constraint('fk_jobs_company_id', type_='foreignkey')
            batch_op.create_foreign_key('fk_jobs_company_id', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
            for name, _ in reversed(_JOB_INDEXES):
                batch_op.drop_index(name)

    op.drop_index(op.f('ix_discovered_items_status'), table_name='discovered_items')
    op.drop_index(op.f('ix_applications_current_stage'), table_name='applications')
