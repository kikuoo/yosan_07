from flask import Flask, request, render_template, redirect, url_for, make_response, flash
from flask_login import login_user, logout_user, login_required, current_user
import os
import logging
from dotenv import load_dotenv
from datetime import datetime
from sqlalchemy import inspect

from app.extensions import db, migrate, login_manager

# 環境変数の読み込み
load_dotenv()

# 工種の定義
CONSTRUCTION_TYPES = {
    '41-01': '準備費',
    '41-02': '仮設物費',
    '41-03': '廃棄物処分費',
    '41-04': '共通仮設',
    '41-05': '直接仮設工事',
    '41-90': '仮設工事一式',
    '42-01': '土工事',
    '42-02': '地業工事',
    '42-03': '鉄筋工事',
    '42-04': '型枠工事',
    '42-05': 'コンクリート工事',
    '42-06': '鉄骨工事',
    '42-07': '組積ALC工事',
    '42-08': '防水工事',
    '42-09': '石工事',
    '42-10': 'タイル工事',
    '42-11': '木工事',
    '42-12': '屋根工事',
    '42-13': '外装工事',
    '42-14': '金属工事',
    '42-15': '左官工事',
    '42-16': '木製建具工事',
    '42-17': '金属製建具工事',
    '42-18': '硝子工事',
    '42-19': '塗装吹付工事',
    '42-20': '内装工事',
    '42-21': '家具・雑工事',
    '42-22': '仮設事務所工事',
    '42-23': 'プール工事',
    '42-24': 'サイン工事',
    '42-25': '厨房機器工事',
    '42-26': '既存改修工事',
    '42-27': '特殊付帯工事',
    '42-28': '住宅設備工事',
    '42-29': '雑工事',
    '42-90': '建築工事一式',
    '43-01': '解体工事',
    '43-02': '外構開発工事',
    '43-03': '附帯建物工事',
    '43-04': '別途外構工事',
    '43-05': '山留工事',
    '43-06': '杭工事',
    '43-90': '解体外構附帯工事一式',
    '44-01': '電気設備工事',
    '44-02': '給排水衛生設備工事',
    '44-03': '空調換気設備工事',
    '44-04': '浄化槽工事',
    '44-05': '昇降機工事',
    '44-06': 'オイル配管設備工事',
    '44-07': '厨房機器工事',
    '44-08': 'ガス設備工事',
    '44-09': '消防設備工事',
    '44-90': '設備工事一式',
    '44-91': '諸経費',
    '45-01': '追加変更工事',
    '45-02': '追加変更工事２',
    '45-10': 'その他工事',
    '45-90': '追加変更一式',
    '46-01': '建築一式工事',
    '46-02': '許認可代顔料',
    '46-10': 'その他工事',
    '61-01': '管理給与',
    '61-02': '共通給与',
    '61-03': '舗装給与',
    '61-04': '建設業退職金共済掛金',
    '61-06': '油脂費',
    '61-10': '法定福利費（労災保険）',
    '61-15': '事務用品費',
    '61-16': '通信交通費',
    '61-18': '租税公課（印紙）',
    '61-20': '保険料（工事保険）',
    '61-22': '福利厚生費（被服・薬品）',
    '61-25': '設計費（施工図費）',
    '61-30': '雑費（打ち合わせ・式典）'
}

def create_app():
    app = Flask(__name__)
    
    # ログ設定
    app.logger.setLevel(logging.INFO)
    
    # 基本設定
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    
    # データベース設定
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        app.logger.error('DATABASE_URL環境変数が設定されていません')
        raise ValueError('DATABASE_URL環境変数が必要です')
    
    # RenderのPostgreSQLアドオン用の設定
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.logger.info('PostgreSQL接続URLを修正しました')
    
    app.logger.info(f'データベース接続URL: {database_url}')
    
    # SSL設定の追加（Render環境用）
    if os.environ.get('PRODUCTION', 'false').lower() == 'true':
        app.logger.info('本番環境用のSSL設定を適用します')
        if '?' not in database_url:
            database_url += '?sslmode=require'
        else:
            database_url += '&sslmode=require'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # セッション設定
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('PRODUCTION', 'false').lower() == 'true'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # 拡張機能の初期化
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # モデルのインポート（循環インポートを避けるため、ここでインポート）
    from app.models import User, Property, ConstructionBudget, Payment
    
    # データベースの初期化
    try:
        with app.app_context():
            # テーブルの存在確認
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            app.logger.info(f'既存のテーブル: {existing_tables}')
            
            # テーブルが存在しない場合は作成
            required_tables = {'user', 'property', 'construction_budget', 'payment'}
            missing_tables = required_tables - set(existing_tables)
            
            if missing_tables:
                app.logger.info(f'作成が必要なテーブル: {missing_tables}')
                db.create_all()
                app.logger.info('データベーステーブルを作成しました')
            
            # payment テーブルの is_contract カラムの確認と追加
            if 'payment' in existing_tables:
                columns = {column['name'] for column in inspector.get_columns('payment')}
                if 'is_contract' not in columns:
                    app.logger.info('payment テーブルに is_contract カラムを追加します')
                    with db.engine.connect() as conn:
                        conn.execute(db.text('ALTER TABLE payment ADD COLUMN is_contract BOOLEAN NOT NULL DEFAULT TRUE'))
                        conn.commit()
                    app.logger.info('is_contract カラムを追加しました')
            
            # 管理者ユーザーの作成（テーブル作成直後のみ）
            if 'user' in missing_tables:
                admin = User.query.filter_by(username='admin').first()
                if not admin:
                    admin = User(
                        username='admin',
                        email='admin@example.com',
                        is_admin=True
                    )
                    admin.set_password('admin')
                    db.session.add(admin)
                    db.session.commit()
                    app.logger.info('管理者ユーザーを作成しました')
            
    except Exception as e:
        app.logger.error(f'データベース初期化エラー: {str(e)}')
        app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
        app.logger.error(f'データベース接続URL: {database_url}')
        if hasattr(e, 'orig'):
            app.logger.error(f'原因: {str(e.orig)}')
        raise
    
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
            error = request.args.get('error')
            error_message = ''
            if error == 'invalid_credentials':
                error_message = '<div class="alert alert-danger">ユーザー名またはパスワードが正しくありません</div>'
            elif error == 'missing_fields':
                error_message = '<div class="alert alert-danger">ユーザー名とパスワードを入力してください</div>'
            elif error == 'system_error':
                error_message = '<div class="alert alert-danger">ログイン処理中にエラーが発生しました。しばらく待ってから再度お試しください。</div>'
            
            return f'''
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
                                    {error_message}
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
        
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                app.logger.warning('ログイン失敗: ユーザー名またはパスワードが入力されていません')
                return redirect('/login?error=missing_fields')
            
            user = User.query.filter_by(username=username).first()
            if user is None or not user.check_password(password):
                app.logger.warning(f'ログイン失敗: ユーザー名またはパスワードが正しくありません')
                return redirect('/login?error=invalid_credentials')
            
            login_user(user)
            app.logger.info(f'ログイン成功: ユーザー "{username}"')
            return redirect('/budgets')
            
        except Exception as e:
            app.logger.error(f'ログイン処理エラー: {str(e)}')
            app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
            return redirect('/login?error=system_error')

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
                        <div class="btn-group" role="group">
                            <a href="/property/{property.id}" class="btn btn-sm btn-info">工種一覧</a>
                            <button type="button" class="btn btn-sm btn-warning" data-bs-toggle="modal" data-bs-target="#editPropertyModal{property.id}">
                                編集
                            </button>
                            <button type="button" class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#deletePropertyModal{property.id}">
                                削除
                            </button>
                        </div>

                        <!-- 編集モーダル -->
                        <div class="modal fade" id="editPropertyModal{property.id}" tabindex="-1">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">物件編集</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <form action="/property/{property.id}/edit" method="POST">
                                            <div class="mb-3">
                                                <label for="code" class="form-label">物件コード</label>
                                                <input type="text" class="form-control" id="code" name="code" value="{property.code}" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="name" class="form-label">物件名</label>
                                                <input type="text" class="form-control" id="name" name="name" value="{property.name}" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="contract_amount" class="form-label">契約金額</label>
                                                <input type="number" class="form-control" id="contract_amount" name="contract_amount" value="{property.contract_amount}" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="budget_amount" class="form-label">予算金額</label>
                                                <input type="number" class="form-control" id="budget_amount" name="budget_amount" value="{property.budget_amount}" required>
                                            </div>
                                            <div class="text-end">
                                                <button type="submit" class="btn btn-primary">更新</button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 削除確認モーダル -->
                        <div class="modal fade" id="deletePropertyModal{property.id}" tabindex="-1">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">物件削除の確認</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <p>物件「{property.name}」を削除してもよろしいですか？</p>
                                        <p class="text-danger">この操作は取り消せません。</p>
                                    </div>
                                    <div class="modal-footer">
                                        <form action="/property/{property.id}/delete" method="POST">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                                            <button type="submit" class="btn btn-danger">削除</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
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

    @app.route('/property/add', methods=['POST'])
    @login_required
    def add_property():
        try:
            code = request.form.get('code')
            name = request.form.get('name')
            contract_amount = request.form.get('contract_amount')
            budget_amount = request.form.get('budget_amount')
            
            # 入力値の検証
            if not all([code, name, contract_amount, budget_amount]):
                app.logger.error('必須項目が入力されていません')
                return redirect('/budgets')
            
            # 物件コードの重複チェック
            if Property.query.filter_by(code=code).first() is not None:
                app.logger.error('この物件コードは既に使用されています')
                return redirect('/budgets')
            
            # 新規物件の作成
            property = Property(
                code=code,
                name=name,
                contract_amount=int(contract_amount),
                budget_amount=int(budget_amount),
                user_id=current_user.id
            )
            
            db.session.add(property)
            db.session.commit()
            app.logger.info(f'新規物件を登録しました: {code}')
            
            return redirect('/budgets')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'物件登録エラー: {str(e)}')
            return redirect('/budgets')

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

    @app.route('/property/<int:property_id>')
    @login_required
    def property_detail(property_id):
        try:
            property = Property.query.get_or_404(property_id)
            
            # 権限チェック
            if property.user_id != current_user.id:
                return redirect('/budgets')
            
            # 工種一覧の取得
            budgets = ConstructionBudget.query.filter_by(property_id=property_id).all()
            
            # 工種リストのHTML生成
            budgets_html = ''
            total_amount = 0
            for budget in budgets:
                total_amount += budget.amount
                
                # 支払い情報の取得と集計
                payments = Payment.query.filter_by(budget_id=budget.id).all()
                contract_payments = [p for p in payments if p.is_contract]
                non_contract_payments = [p for p in payments if not p.is_contract]
                contract_total = sum(p.amount for p in contract_payments)
                non_contract_total = sum(p.amount for p in non_contract_payments)
                total_paid = contract_total + non_contract_total
                remaining = budget.amount - total_paid

                # 支払いリストのHTML生成
                payments_html = ''
                if payments:
                    payments_html = '<div class="mt-3"><h6>支払い履歴</h6><table class="table table-sm"><thead><tr><th>年月</th><th>業者名</th><th>金額</th><th>区分</th><th>備考</th></tr></thead><tbody>'
                    for payment in sorted(payments, key=lambda x: (x.year, x.month)):
                        payment_type = "請負" if payment.is_contract else "請負外"
                        payments_html += f'''
                        <tr>
                            <td>{payment.year}年{payment.month}月</td>
                            <td>{payment.vendor_name}</td>
                            <td>{payment.amount:,}円</td>
                            <td>{payment_type}</td>
                            <td>{payment.note or ''}</td>
                        </tr>
                        '''
                    payments_html += '</tbody></table></div>'

                budgets_html += f'''
                <tr>
                    <td>{budget.code}</td>
                    <td>{budget.name}</td>
                    <td>{budget.amount:,}円</td>
                    <td>
                        <div>請負支払計: {contract_total:,}円</div>
                        <div>請負外支払計: {non_contract_total:,}円</div>
                        <div>支払残: {remaining:,}円</div>
                    </td>
                    <td>
                        <div class="btn-group" role="group">
                            <button type="button" class="btn btn-sm btn-info" data-bs-toggle="modal" data-bs-target="#paymentModal{budget.id}">
                                支払い入力
                            </button>
                            <button type="button" class="btn btn-sm btn-warning" data-bs-toggle="modal" data-bs-target="#editBudgetModal{budget.id}">
                                編集
                            </button>
                            <button type="button" class="btn btn-sm btn-danger" data-bs-toggle="modal" data-bs-target="#deleteBudgetModal{budget.id}">
                                削除
                            </button>
                        </div>
                        {payments_html}

                        <!-- 支払い入力モーダル -->
                        <div class="modal fade" id="paymentModal{budget.id}" tabindex="-1">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">支払い入力</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <form action="/budget/{budget.id}/payment/add" method="POST">
                                            <div class="row mb-3">
                                                <div class="col">
                                                    <label for="payment_year" class="form-label">年</label>
                                                    <input type="number" class="form-control" id="payment_year" name="payment_year" required min="2000" max="2100">
                                                </div>
                                                <div class="col">
                                                    <label for="payment_month" class="form-label">月</label>
                                                    <input type="number" class="form-control" id="payment_month" name="payment_month" required min="1" max="12">
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <label for="vendor_name" class="form-label">業者名</label>
                                                <input type="text" class="form-control" id="vendor_name" name="vendor_name" required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="payment_amount" class="form-label">金額</label>
                                                <input type="number" class="form-control" id="payment_amount" name="payment_amount" required>
                                            </div>
                                            <div class="mb-3">
                                                <div class="form-check">
                                                    <input class="form-check-input" type="radio" name="is_contract" id="is_contract_true{budget.id}" value="true" checked>
                                                    <label class="form-check-label" for="is_contract_true{budget.id}">
                                                        請負
                                                    </label>
                                                </div>
                                                <div class="form-check">
                                                    <input class="form-check-input" type="radio" name="is_contract" id="is_contract_false{budget.id}" value="false">
                                                    <label class="form-check-label" for="is_contract_false{budget.id}">
                                                        請負外
                                                    </label>
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <label for="payment_note" class="form-label">備考</label>
                                                <textarea class="form-control" id="payment_note" name="payment_note" rows="3"></textarea>
                                            </div>
                                            <div class="text-end">
                                                <button type="submit" class="btn btn-primary">登録</button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 工種編集モーダル -->
                        <div class="modal fade" id="editBudgetModal{budget.id}" tabindex="-1">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">工種編集</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <form action="/budget/{budget.id}/edit" method="POST">
                                            <div class="mb-3">
                                                <label for="code" class="form-label">工種コード</label>
                                                <select class="form-select" id="code" name="code" onchange="updateConstructionName(this)" required>
                                                    <option value="">工種を選択してください</option>
''' + '\n'.join([f'                                                    <option value="{code}" data-name="{name}" {"selected" if code == budget.code else ""}>{code} - {name}</option>' for code, name in CONSTRUCTION_TYPES.items()]) + f'''
                                                </select>
                                            </div>
                                            <div class="mb-3">
                                                <label for="name" class="form-label">工種名</label>
                                                <input type="text" class="form-control" id="name" name="name" value="{budget.name}" readonly required>
                                            </div>
                                            <div class="mb-3">
                                                <label for="amount" class="form-label">金額</label>
                                                <input type="number" class="form-control" id="amount" name="amount" value="{budget.amount}" required>
                                            </div>
                                            <div class="text-end">
                                                <button type="submit" class="btn btn-primary">更新</button>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 工種削除確認モーダル -->
                        <div class="modal fade" id="deleteBudgetModal{budget.id}" tabindex="-1">
                            <div class="modal-dialog">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h5 class="modal-title">工種削除の確認</h5>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                                    </div>
                                    <div class="modal-body">
                                        <p>工種「{budget.name}」を削除してもよろしいですか？</p>
                                        <p class="text-danger">この操作は取り消せません。</p>
                                    </div>
                                    <div class="modal-footer">
                                        <form action="/budget/{budget.id}/delete" method="POST">
                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">キャンセル</button>
                                            <button type="submit" class="btn btn-danger">削除</button>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </td>
                </tr>
                '''
            
            return f'''
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="utf-8">
                <title>{property.name} - 工種一覧 - 予算管理システム</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
            </head>
            <body>
                <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
                    <div class="container">
                        <a class="navbar-brand" href="/">予算管理システム</a>
                        <div class="navbar-nav ms-auto">
                            <a class="nav-link" href="/budgets">物件一覧</a>
                            <a class="nav-link" href="/logout">ログアウト</a>
                        </div>
                    </div>
                </nav>
                
                <div class="container mt-4">
                    <div class="row mb-4">
                        <div class="col">
                            <h2>{property.name} - 工種一覧</h2>
                            <p>契約金額: {property.contract_amount:,}円 / 予算金額: {property.budget_amount:,}円</p>
                            <p>工種合計: {total_amount:,}円</p>
                        </div>
                        <div class="col text-end">
                            <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addBudgetModal">
                                新規工種登録
                            </button>
                        </div>
                    </div>
                    
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>工種コード</th>
                                    <th>工種名</th>
                                    <th>予算金額</th>
                                    <th>支払状況</th>
                                    <th>操作</th>
                                </tr>
                            </thead>
                            <tbody>
                                {budgets_html}
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- 新規工種登録モーダル -->
                <div class="modal fade" id="addBudgetModal" tabindex="-1">
                    <div class="modal-dialog">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">新規工種登録</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                <form action="/property/{property_id}/budget/add" method="POST">
                                    <div class="mb-3">
                                        <label for="code" class="form-label">工種コード</label>
                                        <select class="form-select" id="code" name="code" onchange="updateConstructionName(this)" required>
                                            <option value="">工種を選択してください</option>
''' + '\n'.join([f'                                            <option value="{code}" data-name="{name}">{code} - {name}</option>' for code, name in CONSTRUCTION_TYPES.items()]) + '''
                                        </select>
                                    </div>
                                    <div class="mb-3">
                                        <label for="name" class="form-label">工種名</label>
                                        <input type="text" class="form-control" id="name" name="name" readonly required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="amount" class="form-label">金額</label>
                                        <input type="number" class="form-control" id="amount" name="amount" required>
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
                <script>
                    function updateConstructionName(selectElement) {
                        const nameInput = selectElement.closest('.modal-body').querySelector('[name="name"]');
                        const selectedOption = selectElement.options[selectElement.selectedIndex];
                        nameInput.value = selectedOption.value ? selectedOption.dataset.name : '';
                    }
                </script>
            </body>
            </html>
            '''
        except Exception as e:
            app.logger.error(f'工種一覧ページ処理エラー: {str(e)}')
            app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
            return redirect('/budgets')

    @app.route('/property/<int:property_id>/edit', methods=['POST'])
    @login_required
    def edit_property(property_id):
        try:
            property = Property.query.get_or_404(property_id)
            
            # 権限チェック
            if property.user_id != current_user.id:
                return redirect('/budgets')
            
            code = request.form.get('code')
            name = request.form.get('name')
            contract_amount = request.form.get('contract_amount')
            budget_amount = request.form.get('budget_amount')
            
            if not all([code, name, contract_amount, budget_amount]):
                return redirect('/budgets')
            
            # コードの重複チェック（自分以外）
            existing = Property.query.filter(Property.code == code, Property.id != property_id).first()
            if existing is not None:
                return redirect('/budgets')
            
            property.code = code
            property.name = name
            property.contract_amount = int(contract_amount)
            property.budget_amount = int(budget_amount)
            
            db.session.commit()
            app.logger.info(f'物件を更新しました: {code}')
            
            return redirect('/budgets')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'物件更新エラー: {str(e)}')
            return redirect('/budgets')

    @app.route('/property/<int:property_id>/delete', methods=['POST'])
    @login_required
    def delete_property(property_id):
        try:
            property = Property.query.get_or_404(property_id)
            
            # 権限チェック
            if property.user_id != current_user.id:
                return redirect('/budgets')
            
            # 関連する工種を削除
            ConstructionBudget.query.filter_by(property_id=property_id).delete()
            
            # 物件を削除
            db.session.delete(property)
            db.session.commit()
            app.logger.info(f'物件を削除しました: {property.code}')
            
            return redirect('/budgets')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'物件削除エラー: {str(e)}')
            return redirect('/budgets')

    @app.route('/property/<int:property_id>/budget/add', methods=['POST'])
    @login_required
    def add_budget(property_id):
        try:
            property = Property.query.get_or_404(property_id)
            
            # 権限チェック
            if property.user_id != current_user.id:
                return redirect(f'/property/{property_id}')
            
            code = request.form.get('code')
            name = request.form.get('name')
            amount = request.form.get('amount')
            
            if not all([code, name, amount]):
                return redirect(f'/property/{property_id}')
            
            budget = ConstructionBudget(
                code=code,
                name=name,
                amount=int(amount),
                property_id=property_id
            )
            
            db.session.add(budget)
            db.session.commit()
            app.logger.info(f'工種を登録しました: {code}')
            
            return redirect(f'/property/{property_id}')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'工種登録エラー: {str(e)}')
            return redirect(f'/property/{property_id}')

    @app.route('/budget/<int:budget_id>/edit', methods=['POST'])
    @login_required
    def edit_budget(budget_id):
        try:
            budget = ConstructionBudget.query.get_or_404(budget_id)
            
            # 権限チェック
            if budget.property.user_id != current_user.id:
                return redirect('/budgets')
            
            code = request.form.get('code')
            name = request.form.get('name')
            amount = request.form.get('amount')
            
            if not all([code, name, amount]):
                return redirect(f'/property/{budget.property_id}')
            
            budget.code = code
            budget.name = name
            budget.amount = int(amount)
            
            db.session.commit()
            app.logger.info(f'工種を更新しました: {code}')
            
            return redirect(f'/property/{budget.property_id}')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'工種更新エラー: {str(e)}')
            return redirect(f'/property/{budget.property_id}')

    @app.route('/budget/<int:budget_id>/delete', methods=['POST'])
    @login_required
    def delete_budget(budget_id):
        try:
            budget = ConstructionBudget.query.get_or_404(budget_id)
            property_id = budget.property_id
            
            # 権限チェック
            if budget.property.user_id != current_user.id:
                return redirect('/budgets')
            
            db.session.delete(budget)
            db.session.commit()
            app.logger.info(f'工種を削除しました: {budget.code}')
            
            return redirect(f'/property/{property_id}')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'工種削除エラー: {str(e)}')
            return redirect(f'/property/{property_id}')

    @app.route('/budget/<int:budget_id>/payment/add', methods=['POST'])
    @login_required
    def add_payment(budget_id):
        try:
            budget = ConstructionBudget.query.get_or_404(budget_id)
            
            # 権限チェック
            if budget.property.user_id != current_user.id:
                return redirect('/budgets')
            
            payment_year = request.form.get('payment_year')
            payment_month = request.form.get('payment_month')
            vendor_name = request.form.get('vendor_name')
            payment_amount = request.form.get('payment_amount')
            is_contract = request.form.get('is_contract') == 'true'
            payment_note = request.form.get('payment_note')
            
            if not all([payment_year, payment_month, vendor_name, payment_amount]):
                return redirect(f'/property/{budget.property_id}')
            
            payment = Payment(
                year=int(payment_year),
                month=int(payment_month),
                vendor_name=vendor_name,
                amount=int(payment_amount),
                is_contract=is_contract,
                note=payment_note,
                budget_id=budget_id
            )
            
            db.session.add(payment)
            db.session.commit()
            app.logger.info(f'支払いを登録しました: {payment_year}年{payment_month}月 - {payment_amount}円')
            
            return redirect(f'/property/{budget.property_id}')
        except Exception as e:
            db.session.rollback()
            app.logger.error(f'支払い登録エラー: {str(e)}')
            return redirect(f'/property/{budget.property_id}')

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