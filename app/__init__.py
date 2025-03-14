from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os

# データベースの設定
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # 基本設定
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yosan.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # データベースの初期化
    db.init_app(app)
    migrate.init_app(app, db)
    
    # ログインマネージャーの初期化
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # ブループリントの登録
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # エラーハンドラの登録
    @app.errorhandler(404)
    def not_found_error(error):
        return '', 200 if request.method == 'HEAD' else 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return '', 500
    
    return app

# アプリケーションインスタンスを作成
app = create_app()