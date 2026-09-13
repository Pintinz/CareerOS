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


def upgrade() -> None:
    op.create_index(op.f('ix_applications_current_stage'), 'applications', ['current_stage'], unique=False)
    op.create_index(op.f('ix_discovered_items_status'), 'discovered_items', ['status'], unique=False)
    op.create_index(op.f('ix_recruitment_email_events_status'), 'recruitment_email_events', ['status'], unique=False)

    # The original jobs.company_id foreign key is anonymous (defined inline in the very first
    # migration) — SQLite can't target an unnamed constraint with drop_constraint by name unless
    # batch mode's reflection is told what to call it. A `naming_convention` on batch_alter_table
    # gives the reflected anonymous FK a deterministic name so it can actually be dropped, not just
    # shadowed by a second FK on the same column (verified on a fresh DB — see PROJECT_STATUS.md's
    # Phase 9.5 section for why this matters: without it, both the old CASCADE and new RESTRICT FKs
    # ended up coexisting on the rebuilt table). New indexes on the same table are added in this
    # same rebuild rather than a second one for efficiency.
    naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table('jobs', schema=None, recreate='always', naming_convention=naming_convention) as batch_op:
        batch_op.create_index(op.f('ix_jobs_application_deadline'), ['application_deadline'], unique=False)
        batch_op.create_index(op.f('ix_jobs_expires_at'), ['expires_at'], unique=False)
        batch_op.create_index(op.f('ix_jobs_is_active'), ['is_active'], unique=False)
        batch_op.create_index(op.f('ix_jobs_published_at'), ['published_at'], unique=False)
        batch_op.create_index(op.f('ix_jobs_status'), ['status'], unique=False)
        batch_op.drop_constraint('fk_jobs_company_id', type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_jobs_company_id', 'companies', ['company_id'], ['id'], ondelete='RESTRICT'
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_recruitment_email_events_status'), table_name='recruitment_email_events')

    naming_convention = {"fk": "fk_%(table_name)s_%(column_0_name)s"}
    with op.batch_alter_table('jobs', schema=None, recreate='always', naming_convention=naming_convention) as batch_op:
        batch_op.drop_constraint('fk_jobs_company_id', type_='foreignkey')
        batch_op.create_foreign_key('fk_jobs_company_id', 'companies', ['company_id'], ['id'], ondelete='CASCADE')
        batch_op.drop_index(op.f('ix_jobs_status'))
        batch_op.drop_index(op.f('ix_jobs_published_at'))
        batch_op.drop_index(op.f('ix_jobs_is_active'))
        batch_op.drop_index(op.f('ix_jobs_expires_at'))
        batch_op.drop_index(op.f('ix_jobs_application_deadline'))

    op.drop_index(op.f('ix_discovered_items_status'), table_name='discovered_items')
    op.drop_index(op.f('ix_applications_current_stage'), table_name='applications')
