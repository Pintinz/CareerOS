"""phase 11 widen audit_logs entity_id

Revision ID: 45e5467ab49d
Revises: 4b229d578314
Create Date: 2026-09-13 19:04:35.751295

Found by running the suite against PostgreSQL: entity_id was VARCHAR(36), sized for UUIDs, but
system settings are audited by key and "email_classifier_confidence_thresholds" is 38 characters.
PostgreSQL rejects the insert (SQLite ignores VARCHAR lengths), so the setting change committed with
no audit record.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45e5467ab49d'
down_revision: Union[str, None] = '4b229d578314'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == 'sqlite':
        # SQLite doesn't enforce the length; rebuild only to keep the declared schema accurate.
        with op.batch_alter_table('audit_logs', schema=None) as batch_op:
            batch_op.alter_column('entity_id', existing_type=sa.String(36), type_=sa.String(255), existing_nullable=True)
    else:
        op.alter_column('audit_logs', 'entity_id', existing_type=sa.String(36), type_=sa.String(255), existing_nullable=True)


def downgrade() -> None:
    # Shrinking would fail (or truncate) if any audited key is longer than 36 characters, which is
    # exactly the case this migration exists for — refuse loudly rather than lose audit data.
    raise NotImplementedError("Irreversible: audit_logs.entity_id may hold values longer than 36 characters.")
