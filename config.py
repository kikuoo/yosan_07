from app import app
import os

# PostgreSQL接続設定
database_url = os.getenv('DATABASE_URL')

# render.comのPostgreSQLでは "postgres://" で始まるURLが提供されるため、
# SQLAlchemyが期待する "postgresql://" に変換
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url 