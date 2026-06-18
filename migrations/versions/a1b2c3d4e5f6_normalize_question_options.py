"""normalize question options into question_options table

Revision ID: a1b2c3d4e5f6
Revises: 3ea9d360bd11
Create Date: 2026-06-18 12:00:00.000000

"""
import json
import uuid
from collections import defaultdict
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '3ea9d360bd11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table descriptors for the data migration.
_questions = sa.table(
    'questions',
    sa.column('id', sa.Uuid()),
    sa.column('options', sa.JSON()),
    sa.column('correct_option_index', sa.Integer()),
)
_options = sa.table(
    'question_options',
    sa.column('id', sa.Uuid()),
    sa.column('question_id', sa.Uuid()),
    sa.column('position', sa.Integer()),
    sa.column('text', sa.String()),
    sa.column('is_correct', sa.Boolean()),
)


def upgrade() -> None:
    """Split questions.options (JSON) into one question_options row per option."""
    op.create_table(
        'question_options',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('text', sa.String(length=500), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('question_id', 'position', name='uq_option_question_position'),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.select(_questions.c.id, _questions.c.options, _questions.c.correct_option_index)
    ).fetchall()

    to_insert = []
    for qid, options, correct_index in rows:
        if isinstance(options, str):  # SQLite returns JSON as text
            options = json.loads(options)
        for position, text in enumerate(options or []):
            to_insert.append({
                'id': uuid.uuid4(),
                'question_id': qid,
                'position': position,
                'text': text,
                'is_correct': position == correct_index,
            })

    if to_insert:
        bind.execute(sa.insert(_options), to_insert)

    with op.batch_alter_table('questions') as batch_op:
        batch_op.drop_column('correct_option_index')
        batch_op.drop_column('options')


def downgrade() -> None:
    """Rebuild the JSON options array and correct index from the option rows."""
    with op.batch_alter_table('questions') as batch_op:
        batch_op.add_column(sa.Column('options', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('correct_option_index', sa.Integer(), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(
        sa.select(
            _options.c.question_id,
            _options.c.position,
            _options.c.text,
            _options.c.is_correct,
        ).order_by(_options.c.question_id, _options.c.position)
    ).fetchall()

    texts: dict = defaultdict(list)
    correct: dict = {}
    for qid, position, text, is_correct in rows:
        texts[qid].append(text)
        if is_correct:
            correct[qid] = position

    for qid, opts in texts.items():
        bind.execute(
            sa.update(_questions)
            .where(_questions.c.id == qid)
            .values(options=opts, correct_option_index=correct.get(qid, 0))
        )

    # Enforce the original NOT NULL constraints (every question has >= 2 options
    # by domain rule, so no NULLs remain after the backfill above).
    with op.batch_alter_table('questions') as batch_op:
        batch_op.alter_column('options', existing_type=sa.JSON(), nullable=False)
        batch_op.alter_column('correct_option_index', existing_type=sa.Integer(), nullable=False)

    op.drop_table('question_options')
