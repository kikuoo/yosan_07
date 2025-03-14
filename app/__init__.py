from flask import Flask, request, render_template
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
    app.register_blueprint(main_bp)
    app.logger.info('メインブループリントを登録しました')
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.logger.info('認証ブループリントを登録しました')
    
    # テンプレートフィルターの登録
    @app.template_filter('format_currency')
    def format_currency(value):
        if value is None:
            return '0'
        return f'{value:,}'
    
    # ルートの登録を確認
    app.logger.info('登録されたルート:')
    for rule in app.url_map.iter_rules():
        app.logger.info(f'{rule.endpoint}: {rule.methods} {rule}')
    
    # エラーハンドラの登録
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.error(f'404エラー: {request.url}')
        return render_template('error.html', error='ページが見つかりません'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500エラー: {str(error)}')
        return render_template('error.html', error='サーバーエラーが発生しました'), 500
    
    return app

# アプリケーションインスタンスを作成
app = create_app()

# User モデルをグローバルにエクスポート
from app.models import User