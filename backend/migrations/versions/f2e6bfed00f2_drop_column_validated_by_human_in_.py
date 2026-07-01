"""DROP column validated_by_human in DescriptionByIA

Revision ID: f2e6bfed00f2
Revises: af54b3df9281
Create Date: 2026-05-26 10:40:05.266764

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f2e6bfed00f2'
down_revision: Union[str, Sequence[str], None] = 'af54b3df9281'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # La colonne n'existe pas sur les nouvelles installations (af54b3df9281 ne la crée pas),
    # mais elle peut exister sur des BDD créées avant ce refactor. On utilise IF EXISTS.
    op.execute('ALTER TABLE "DescriptionByIA" DROP COLUMN IF EXISTS validated_by_human')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        'ALTER TABLE "DescriptionByIA"'
        ' ADD COLUMN IF NOT EXISTS validated_by_human BOOLEAN NOT NULL DEFAULT false'
    )
