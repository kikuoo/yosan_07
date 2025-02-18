"""add format currency filter

Revision ID: add_format_currency
Revises: previous_revision_id
Create Date: 2025-02-15 00:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_format_currency'
down_revision = 'previous_revision_id'  # 前回のマイグレーションIDを指定
branch_labels = None
depends_on = None

def upgrade():
    # format_currencyフィルターはPythonコードの変更のみで、
    # データベースの変更は必要ありません
    pass

def downgrade():
    pass 