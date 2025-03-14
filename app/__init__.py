from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
from urllib.parse import urlparse

# データベースの設定
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///yosan.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # データベースの設定
    database_url = os.environ.get('DATABASE_URL', '').strip()
    if not database_url:
        database_url = 'sqlite:///yosan.db'
    elif database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    
    # データベースとログインマネージャーの初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # モデルのインポート
    from app import models
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # ブループリントの登録
    from app.main import bp as main_bp
    app.register_blueprint(main_bp, url_prefix='/')
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # テンプレートフィルターの登録
    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return '0'
        return f'{value:,}'
    
    return app

# アプリケーションインスタンスを作成
app = create_app()

# User モデルをグローバルにエクスポート
from app.models import User