from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
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
    login_manager.login_view = 'login'
    
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

    # ルートの定義
    @app.route('/')
    def index():
        return '''
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
                            <a href="/login" class="btn btn-primary btn-lg">ログイン</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return '''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>ログイン - 予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h4 class="mb-0">ログイン</h4>
                                </div>
                                <div class="card-body">
                                    <form method="POST">
                                        <div class="mb-3">
                                            <label for="username" class="form-label">ユーザー名</label>
                                            <input type="text" class="form-control" id="username" name="username" required>
                                        </div>
                                        <div class="mb-3">
                                            <label for="password" class="form-label">パスワード</label>
                                            <input type="password" class="form-control" id="password" name="password" required>
                                        </div>
                                        <div class="d-grid gap-2">
                                            <button type="submit" class="btn btn-primary">ログイン</button>
                                            <a href="/register" class="btn btn-secondary">新規登録</a>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return redirect('/login')
        
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            return redirect('/login')
        
        login_user(user)
        return redirect('/budgets')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect('/')

    @app.route('/budgets')
    @login_required
    def budgets():
        try:
            app.logger.info('予算ページへのアクセス')
            app.logger.info(f'ユーザーID: {current_user.id}')
            from app.models import Property
            properties = Property.query.filter_by(user_id=current_user.id).all()
            
            # 物件リストのHTMLを生成
            properties_html = ''
            for property in properties:
                properties_html += f'''
                <tr>
                    <td>{property.code}</td>
                    <td>{property.name}</td>
                    <td>{property.contract_amount:,}円</td>
                    <td>{property.budget_amount:,}円</td>
                    <td>
                        <a href="/property/{property.id}" class="btn btn-sm btn-info">詳細</a>
                    </td>
                </tr>
                '''
            
            return f'''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>物件一覧 - 予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
                    <div class="container">
                        <a class="navbar-brand" href="/">予算管理システム</a>
                        <div class="navbar-nav ms-auto">
                            <a class="nav-link" href="/logout">ログアウト</a>
                        </div>
                    </div>
                </nav>
                
                <div class="container mt-4">
                    <div class="row mb-4">
                        <div class="col">
                            <h2>物件一覧</h2>
                        </div>
                        <div class="col text-end">
                            <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addPropertyModal">
                                新規物件登録
                            </button>
                        </div>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>物件コード</th>
                                    <th>物件名</th>
                                    <th>契約金額</th>
                                    <th>予算金額</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {properties_html}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 新規物件登録モーダル -->
                <div class="modal fade" id="addPropertyModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">新規物件登録</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <form action="/property/add" method="POST">
                                    <div class="mb-3">
                                        <label for="code" class="form-label">物件コード</label>
                                        <input type="text" class="form-control" id="code" name="code" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="name" class="form-label">物件名</label>
                                        <input type="text" class="form-control" id="name" name="name" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="contract_amount" class="form-label">契約金額</label>
                                        <input type="number" class="form-control" id="contract_amount" name="contract_amount" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="budget_amount" class="form-label">予算金額</label>
                                        <input type="number" class="form-control" id="budget_amount" name="budget_amount" required>
                                    </div>
                                    <div class="text-end">
                                        <button type="submit" class="btn btn-primary">登録</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>

                <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
            </body>
            </html>
            '''
        except Exception as e:
            app.logger.error(f'予算ページ処理エラー: {str(e)}')
            app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
            return redirect('/')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'GET':
            return '''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>新規登録 - 予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <div class="container mt-5">
                    <div class="row justify-content-center">
                        <div class="col-md-6">
                            <div class="card">
                                <div class="card-header">
                                    <h4 class="mb-0">新規登録</h4>
                                </div>
                                <div class="card-body">
                                    <form method="POST">
                                        <div class="mb-3">
                                            <label for="username" class="form-label">ユーザー名</label>
                                            <input type="text" class="form-control" id="username" name="username" required>
                                        </div>
                                        <div class="mb-3">
                                            <label for="email" class="form-label">メールアドレス</label>
                                            <input type="email" class="form-control" id="email" name="email" required>
                                        </div>
                                        <div class="mb-3">
                                            <label for="password" class="form-label">パスワード</label>
                                            <input type="password" class="form-control" id="password" name="password" required>
                                        </div>
                                        <div class="mb-3">
                                            <label for="confirm_password" class="form-label">パスワード（確認）</label>
                                            <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
                                        </div>
                                        <div class="d-grid gap-2">
                                            <button type="submit" class="btn btn-primary">登録</button>
                                            <a href="/login" class="btn btn-secondary">ログインに戻る</a>
                                        </div>
                                    </form>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            '''
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not email or not password or not confirm_password:
            return redirect('/register')
        
        if password != confirm_password:
            return redirect('/register')
        
        # ユーザー名とメールアドレスの重複チェック
        if User.query.filter_by(username=username).first() is not None:
            return redirect('/register')
        if User.query.filter_by(email=email).first() is not None:
            return redirect('/register')
        
        # 新規ユーザーの作成
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
            login_user(user)
            return redirect('/budgets')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'ユーザー登録エラー: {str(e)}')
            return redirect('/register')

    # エラーハンドラ
    @app.errorhandler(404)
    def not_found_error(error):
        if request.method == 'HEAD':
            return '', 200
        return '''
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="utf-8">
            <title>ページが見つかりません - 予算管理システム</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6 text-center">
                        <h1>ページが見つかりません</h1>
                        <div class="mt-4">
                            <a href="/" class="btn btn-primary">トップページに戻る</a>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''', 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return '''
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
                            <a href="/" class="btn btn-primary">トップページに戻る</a>
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