from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
import os
import logging

# データベースの設定
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # ログ設定
    app.logger.setLevel(logging.INFO)
    
    # 基本設定
    app.config['SECRET_KEY'] = 'dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yosan.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # セッション設定
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # データベースの初期化
    db.init_app(app)
    migrate.init_app(app, db)
    
    # ログインマネージャーの初期化
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    # ユーザーローダーの設定
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return User.query.get(int(user_id))
        except Exception as e:
            app.logger.error(f'ユーザーロード中にエラーが発生しました: {str(e)}')
            return None
    
    with app.app_context():
        # データベースのテーブルを作成
        try:
            db.create_all()
            app.logger.info('データベーステーブルを作成しました')
        except Exception as e:
            app.logger.error(f'データベーステーブルの作成中にエラーが発生しました: {str(e)}')
    
    # ブループリントの登録
    try:
        from app.main import bp as main_bp
        app.register_blueprint(main_bp)
        app.logger.info('メインブループリントを登録しました')
        
        from app.auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.logger.info('認証ブループリントを登録しました')
    except Exception as e:
        app.logger.error(f'ブループリントの登録中にエラーが発生しました: {str(e)}')
    
    # エラーハンドラの登録
    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.info(f'404エラー: {request.url}')
        if request.method == 'HEAD':
            return '', 200
        try:
            return redirect(url_for('auth.login'))
        except Exception as e:
            app.logger.error(f'リダイレクト中にエラーが発生しました: {str(e)}')
            return 'エラーが発生しました', 500
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'500エラー: {str(error)}')
        db.session.rollback()
        try:
            return redirect(url_for('auth.login'))
        except Exception as e:
            app.logger.error(f'リダイレクト中にエラーが発生しました: {str(e)}')
            return 'エラーが発生しました', 500
    
    return app

# アプリケーションインスタンスを作成
app = create_app()