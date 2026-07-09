"""Add cancelled value to task_status enum

Revision ID: 9a1c7e2f5b3d
Revises: 682d342ad907
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9a1c7e2f5b3d'
down_revision: Union[str, Sequence[str], None] = '682d342ad907'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ALTER TYPE ... ADD VALUE ne peut pas s'exécuter à l'intérieur du bloc de
    # transaction géré par Alembic (elle doit être "committée" avant qu'une
    # autre commande n'utilise la nouvelle valeur). On sort donc de cette
    # transaction avant d'ajouter la valeur.
    op.execute("COMMIT")
    op.execute("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL ne permet pas de retirer une valeur d'un type enum. Une tâche
    # annulée devrait être requalifiée manuellement avant tout downgrade.
    pass
