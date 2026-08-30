"""add document status fields

Revision ID: c3a1b2e4d5f6
Revises: 6a690bd1e827
Create Date: 2026-08-29 17:00:00.000000

给 documents 表新增异步处理相关字段
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3a1b2e4d5f6'
down_revision: Union[str, None] = '6a690bd1e827'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 与模型 app/models/document.py 保持一致：
    # status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING)
    # error_message = Column(Text, nullable=True)
    # processed_at = Column(DateTime(timezone=True), nullable=True)
    # celery_task_id = Column(String(100), nullable=True)
    op.add_column('documents', sa.Column(
        'status',
        sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'),
        nullable=True,
        comment='状态'
    ))
    op.add_column('documents', sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'))
    op.add_column('documents', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True, comment='处理时间'))
    op.add_column('documents', sa.Column('celery_task_id', sa.String(length=100), nullable=True, comment='Celery任务ID'))


def downgrade() -> None:
    op.drop_column('documents', 'celery_task_id')
    op.drop_column('documents', 'processed_at')
    op.drop_column('documents', 'error_message')
    op.drop_column('documents', 'status')
