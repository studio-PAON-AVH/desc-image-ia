"""add new table DescriptionByIA and rename ImageDescriptions to DescriptionFinale

Revision ID: af54b3df9281
Revises: bf4038acc964
Create Date: 2026-05-26 10:14:23.234898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'af54b3df9281'
down_revision: Union[str, Sequence[str], None] = 'bf4038acc964'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop l'ancienne table ImageDescriptions (aucune donnée à conserver)
    op.drop_index('idx_image_descriptions_is_written_by_ai', table_name='ImageDescriptions')
    op.drop_index('idx_image_descriptions_is_written_by_human', table_name='ImageDescriptions')
    op.drop_index('idx_image_descriptions_image_id', table_name='ImageDescriptions')
    op.drop_index('idx_image_descriptions_model_ia_id', table_name='ImageDescriptions')
    op.drop_index('idx_image_model', table_name='ImageDescriptions')
    op.drop_table('ImageDescriptions')

    # Nouvelle table DescriptionFinale (description validée/finale par image)
    op.create_table(
        'DescriptionFinale',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('model_ia_id', sa.Integer(), nullable=True),
        sa.Column('description_text', sa.Text(), nullable=False),
        sa.Column('validated_by_human', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['Users.id']),
        sa.ForeignKeyConstraint(['image_id'], ['Images.id']),
        sa.ForeignKeyConstraint(['model_ia_id'], ['ModelsIA.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_desc_finale_image_model', 'DescriptionFinale', ['image_id', 'model_ia_id'], unique=False)
    op.create_index('idx_desc_finale_image_id', 'DescriptionFinale', ['image_id'], unique=False)
    op.create_index('idx_desc_finale_model_ia_id', 'DescriptionFinale', ['model_ia_id'], unique=False)

    # Nouvelle table DescriptionByIA (descriptions brutes générées par chaque modèle)
    op.create_table(
        'DescriptionByIA',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('model_ia_id', sa.Integer(), nullable=False),
        sa.Column('description_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['Images.id']),
        sa.ForeignKeyConstraint(['model_ia_id'], ['ModelsIA.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_desc_by_ia_image_id', 'DescriptionByIA', ['image_id'], unique=False)
    op.create_index('idx_desc_by_ia_image_model', 'DescriptionByIA', ['image_id', 'model_ia_id'], unique=False)
    op.create_index('idx_desc_by_ia_model_ia_id', 'DescriptionByIA', ['model_ia_id'], unique=False)

    op.drop_column('Tasks', 'updated_at')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('Tasks', sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False))

    op.drop_index('idx_desc_by_ia_model_ia_id', table_name='DescriptionByIA')
    op.drop_index('idx_desc_by_ia_image_model', table_name='DescriptionByIA')
    op.drop_index('idx_desc_by_ia_image_id', table_name='DescriptionByIA')
    op.drop_table('DescriptionByIA')

    op.drop_index('idx_desc_finale_model_ia_id', table_name='DescriptionFinale')
    op.drop_index('idx_desc_finale_image_id', table_name='DescriptionFinale')
    op.drop_index('idx_desc_finale_image_model', table_name='DescriptionFinale')
    op.drop_table('DescriptionFinale')

    op.create_table(
        'ImageDescriptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('model_ia_id', sa.Integer(), nullable=True),
        sa.Column('description_text', sa.Text(), nullable=False),
        sa.Column('is_written_by_ai', sa.Boolean(), nullable=False),
        sa.Column('is_written_by_human', sa.Boolean(), nullable=False),
        sa.Column('generated_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('validated_by_human', sa.Boolean(), nullable=False),
        sa.Column('created_at', postgresql.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', postgresql.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['image_id'], ['Images.id']),
        sa.ForeignKeyConstraint(['model_ia_id'], ['ModelsIA.id']),
        sa.PrimaryKeyConstraint('id'),
    )
        
    op.create_index('idx_image_model', 'ImageDescriptions', ['image_id', 'model_ia_id'], unique=False)
    op.create_index('idx_image_descriptions_model_ia_id', 'ImageDescriptions', ['model_ia_id'], unique=False)
    op.create_index('idx_image_descriptions_image_id', 'ImageDescriptions', ['image_id'], unique=False)
    op.create_index('idx_image_descriptions_is_written_by_human', 'ImageDescriptions', ['is_written_by_human'], unique=False)
    op.create_index('idx_image_descriptions_is_written_by_ai', 'ImageDescriptions', ['is_written_by_ai'], unique=False)
