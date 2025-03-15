from flask import Flask, request, render_template, redirect, url_for, make_response
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
    
    # セッション設定を一時的に無効化
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = False
    app.config['SESSION_COOKIE_SAMESITE'] = None
    
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
        return User.query.get(int(user_id))
    
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
    
    # エラーハンドラ
    @app.errorhandler(404)
    def not_found_error(error):
        if request.method == 'HEAD':
            return '', 200
            
        with app.app_context():
            login_url = url_for('auth.login', _external=True)
            return f'''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-6 text-center">
                            <h1>予算管理システム</h1>
                            <div class="mt-4">
                                <a href="{login_url}" class="btn btn-primary btn-lg">ログイン</a>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            ''', 200
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        with app.app_context():
            home_url = url_for('main.index', _external=True)
            return f'''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>エラー - 予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-6 text-center">
                            <h1>エラーが発生しました</h1>
                            <div class="mt-4">
                                <a href="{home_url}" class="btn btn-primary">トップページに戻る</a>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            ''', 500
    
    return app

# アプリケーションインスタンスを作成
app = create_app()