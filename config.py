import os
from dotenv import load_dotenv

load_dotenv()

# 環境変数の設定
FLASK_ENV = os.getenv('FLASK_ENV', 'development')
DATABASE_URL = os.getenv('DATABASE_URL')

# PostgreSQL接続設定
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 本番環境の設定
if FLASK_ENV == 'production':
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = True
else:
    # 開発環境の設定
    SQLALCHEMY_DATABASE_URI = "sqlite:///yosan.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SECURE = False