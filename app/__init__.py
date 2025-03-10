from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# データベースの設定
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # データベースの設定
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # RenderのPostgreSQL URLを修正
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        # データベース名を修正
        if "yosan_psql" in database_url:
            database_url = database_url.replace("yosan_psql", "yosan_psql", 1)
        print(f"データベースURL: {database_url}")
    else:
        database_url = 'sqlite:///app.db'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # データベースとログインマネージャーの初期化
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # モデルのインポート
    from app import models
    
    # ブループリントの登録
    from app.routes import main
    from app.auth import auth
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    return app

# アプリケーションインスタンスを作成
app = create_app() 