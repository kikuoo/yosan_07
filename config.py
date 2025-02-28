import os

# render.comが提供するDATABASE_URLを使用
DATABASE_URL = os.environ.get('DATABASE_URL')

# 注意: render.comのURLは "postgres://" で始まりますが、
# SQLAlchemyは "postgresql://" を期待するため、必要に応じて置換
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLAlchemyの設定
SQLALCHEMY_DATABASE_URI = DATABASE_URL 