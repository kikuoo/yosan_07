from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, init, migrate, upgrade
from datetime import datetime, timezone, timedelta
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import locale
from flask.cli import with_appcontext
import shutil
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# Flaskアプリケーションの設定
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')

# セッション設定
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)  # セッションの有効期限を30日に設定
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPSでのみクッキーを送信
app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScriptからのクッキーアクセスを防止
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

# 環境変数の設定
FLASK_ENV = os.getenv('FLASK_ENV', 'development')

# 環境に応じた設定
if FLASK_ENV == 'production':
    app.config['APPLICATION_ROOT'] = '/yosan'
    app.config['SESSION_COOKIE_PATH'] = '/yosan'
    app.config['SESSION_COOKIE_DOMAIN'] = '.onrender.com'  # render.comのドメインを指定
else:
    app.config['APPLICATION_ROOT'] = '/'
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['SESSION_COOKIE_SECURE'] = False  # 開発環境ではHTTPを許可

app.config['SESSION_COOKIE_NAME'] = 'yosan_session'

# データベースURLの設定
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # PostgreSQLのURLを修正
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    # 環境変数が設定されていない場合は、SQLiteを使用
    print("警告: DATABASE_URLが設定されていません。SQLiteを使用します。")
    DATABASE_URL = "sqlite:///yosan.db"

# SQLAlchemy設定
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# データベースの初期化
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'ログインしてください。'
login_manager.refresh_view = 'login'  # セッション再認証時のビュー
login_manager.needs_refresh_message = 'セッションが切れました。再度ログインしてください。'
login_manager.session_protection = "strong"  # セッション保護を強化

# 日本語ロケールを設定（エラー処理を追加）
try:
    locale.setlocale(locale.LC_ALL, 'ja_JP.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Japanese_Japan.932')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')  # システムのデフォルトロケールを使用

def format_currency(value):
    """通貨を日本円形式でフォーマットする"""
    if value is None:
        return '¥0'
    try:
        return f'¥{value:,}'
    except:
        return f'¥{value}'

def subtract(value1, value2):
    """2つの値の差を計算するフィルター"""
    return value1 - value2

def starts_with(value, prefix):
    """文字列が指定のプレフィックスで始まるかチェックするフィルター"""
    return str(value).startswith(prefix)

# カスタムフィルターを登録
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['subtract'] = subtract
app.jinja_env.filters['starts_with'] = starts_with

# モデル定義
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(50), nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    contract_amount = db.Column(db.Integer, nullable=False)  # 請負金額
    budget_amount = db.Column(db.Integer, nullable=False)    # 当初実行予算額
    current_budget_amount = db.Column(db.Integer)           # カラム名を変更
    target_management_rate = db.Column(db.Float, nullable=False, default=0.0)  # デフォルト値を0.0に設定
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # 関連する工種が削除されるように設定
    work_types = db.relationship('WorkType', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def initial_profit_rate(self):
        """当初利益率を計算"""
        if self.contract_amount > 0:
            return ((self.contract_amount - self.budget_amount) / self.contract_amount) * 100
        return 0

    @property
    def current_profit_rate(self):
        """現在の利益率を計算"""
        if self.contract_amount > 0 and self.current_budget_amount:
            return ((self.contract_amount - self.current_budget_amount) / self.contract_amount) * 100
        return self.initial_profit_rate

    @property
    def budget_difference(self):
        """予算増減額を計算（当初予算 - 工種予算合計）"""
        # 全工種の予算額合計を計算
        total_work_type_budget = sum(work_type.budget_amount for work_type in self.work_types)
        
        # 工種がある場合は（当初予算 - 工種合計）を返す
        if total_work_type_budget > 0:
            return self.budget_amount - total_work_type_budget
        return 0

    @property
    def current_budget(self):
        """現在の実行予算額を計算"""
        # 全工種の予算額合計を計算
        total_work_type_budget = sum(work_type.budget_amount for work_type in self.work_types)
        
        # 工種がある場合は工種合計、ない場合は当初予算を返す
        return total_work_type_budget if total_work_type_budget > 0 else self.budget_amount

    @current_budget.setter
    def current_budget(self, value):
        """現在の実行予算額を設定"""
        self.current_budget_amount = value

    @property
    def target_management_cost(self):
        """目標一般管理費を計算"""
        if self.target_management_rate is not None and self.target_management_rate > 0:
            base_management = self.contract_amount - self.budget_amount
            return base_management * (1 + (self.target_management_rate / 100))
        return self.contract_amount - self.budget_amount

    @property
    def target_management_profit(self):
        """目標一般管理費の利益アップ額を計算"""
        if self.target_management_rate is None or self.target_management_rate <= 0:
            return 0
        base_management = self.contract_amount - self.budget_amount
        return self.target_management_cost - base_management

class WorkType(db.Model):
    __tablename__ = 'work_types'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    work_code = db.Column(db.String(50), nullable=False)
    work_name = db.Column(db.String(200), nullable=False)
    budget_amount = db.Column(db.Integer, nullable=False)
    remaining_amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # 関連する支払い情報が削除されるように設定
    payments = db.relationship('Payment', backref='work_type', lazy=True, cascade='all, delete-orphan')

    @property
    def contract_total(self):
        """請負支払いの合計金額を計算"""
        return sum(payment.amount for payment in self.payments if payment.payment_type == '請負')

    @property
    def non_contract_total(self):
        """請負外支払いの合計金額を計算"""
        return sum(payment.amount for payment in self.payments if payment.payment_type == '請負外')

    @property
    def profit_amount(self):
        """利益計上額の合計を計算"""
        return sum(payment.amount for payment in self.payments if payment.is_profit)

    def calculate_remaining_amount(self):
        """予算残額を計算する。利益計上額を考慮"""
        total_payments = sum(payment.amount for payment in self.payments if not payment.is_profit)
        self.remaining_amount = self.budget_amount - total_payments - self.profit_amount
        return self.remaining_amount

    def get_monthly_non_contract_totals(self):
        """請負外支払いの月別合計を計算"""
        monthly_totals = {}
        for payment in self.payments:
            if payment.payment_type == '請負外' and payment.year > 0:  # 未定の支払いは除外
                key = f"{payment.year}年{payment.month}月"
                if key not in monthly_totals:
                    monthly_totals[key] = 0
                monthly_totals[key] += payment.amount
        
        # 日付順にソート
        sorted_totals = sorted(
            monthly_totals.items(),
            key=lambda x: (int(x[0].split('年')[0]), int(x[0].split('年')[1].split('月')[0]))
        )
        return sorted_totals

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    work_type_id = db.Column(db.Integer, db.ForeignKey('work_types.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    contractor = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    payment_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    is_progress_payment = db.Column(db.Boolean, default=False)  # 出来高払いフラグを追加
    progress_rate = db.Column(db.Float)
    previous_progress = db.Column(db.Float)
    current_progress = db.Column(db.Float)
    contract_id = db.Column(db.Integer, db.ForeignKey('payments.id'))
    is_profit = db.Column(db.Boolean, default=False)  # 利益計上フラグを追加

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        projects = Project.query.order_by(Project.created_at.desc()).all()
        
        # 各プロジェクトの予算関連情報を計算
        for project in projects:
            # 全工種の支払い合計を計算（支払済額）
            total_payments = sum(
                sum(payment.amount for payment in work_type.payments)
                for work_type in project.work_types
            )
            
            # 予算残額を計算
            project.remaining_budget = project.current_budget - total_payments
            
            # 利益額を計算（請負金額 - 予算額）
            project.profit = project.contract_amount - total_payments
            
            # 利益率を計算（利益額 ÷ 請負金額 × 100）
            if project.contract_amount > 0:
                project.profit_rate = (project.profit / project.contract_amount) * 100
            else:
                project.profit_rate = 0
            
            # プロパティを使用して値を取得（代入はしない）
            project.budget_diff = project.budget_difference
        
        return render_template('index.html', projects=projects)
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        budget_amount = int(request.form['budget_amount'])
        
        # current_budgetの処理を修正
        current_budget_str = request.form.get('current_budget', '')
        current_budget = int(current_budget_str) if current_budget_str.strip() else budget_amount
        
        project = Project(
            project_code=request.form['project_code'],
            project_name=request.form['project_name'],
            contract_amount=int(request.form['contract_amount']),
            budget_amount=budget_amount,
            current_budget_amount=current_budget  # カラム名を変更
        )
        db.session.add(project)
        db.session.commit()
        flash('物件を追加しました')
        return redirect(url_for('index'))
    
    return render_template('add_project.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        project.project_code = request.form['project_code']
        project.project_name = request.form['project_name']
        project.contract_amount = int(request.form['contract_amount'])
        project.budget_amount = int(request.form['budget_amount'])
        
        current_budget_str = request.form.get('current_budget', '')
        project.current_budget_amount = int(current_budget_str) if current_budget_str.strip() else project.budget_amount
        
        db.session.commit()
        flash('物件を更新しました')
        return redirect(url_for('index'))
    
    return render_template('edit_project.html', project=project)

@app.route('/projects/<int:project_id>/work_types')
@login_required
def work_type_list(project_id):
    project = Project.query.get_or_404(project_id)
    
    # 全工種を取得（フィルタリング前）
    all_work_types = WorkType.query.filter_by(project_id=project_id).all()
    
    # 契約時現場管理費を計算（61-で始まる工種の合計）
    site_management_cost = sum(
        work_type.budget_amount 
        for work_type in all_work_types 
        if work_type.work_code.startswith('61-')
    )
    
    # 契約時一般管理費を計算（請負金額 - 契約時実行予算額）
    general_management_cost = project.contract_amount - project.budget_amount
    
    # 検索パラメータを取得
    search_code = request.args.get('search_code', '')
    search_contractor = request.args.get('search_contractor', '')
    
    # 工種を取得（コード順にソート）
    work_types = WorkType.query.filter_by(project_id=project_id).order_by(WorkType.work_code).all()
    
    # 業者一覧を取得（重複を除く）
    contractors = db.session.query(Payment.contractor).distinct().join(WorkType).filter(
        WorkType.project_id == project_id
    ).all()
    contractors = [c[0] for c in contractors]
    
    # 検索条件による絞り込み
    filtered_work_types = []
    for work_type in work_types:
        # 工種コードでの絞り込み
        if search_code and work_type.work_code != search_code:
            continue
            
        # 業者名での絞り込み
        if search_contractor:
            payments = [p for p in work_type.payments if search_contractor.lower() in p.contractor.lower()]
            if payments:
                # 支払い情報を業者でフィルタリングしてワークタイプにセット
                work_type.filtered_payments = payments
                filtered_work_types.append(work_type)
        else:
            filtered_work_types.append(work_type)
            work_type.filtered_payments = work_type.payments
    
    # 各工種の残額を計算
    for work_type in filtered_work_types:
        work_type.remaining_amount = work_type.calculate_remaining_amount()
        db.session.add(work_type)
    db.session.commit()
    
    # 全体の支払い合計と残額を計算
    total_payment = sum(
        sum(payment.amount for payment in work_type.payments)
        for work_type in filtered_work_types
    )
    remaining_budget = project.budget_amount - total_payment
    
    return render_template('work_type_list.html', 
                         project=project, 
                         work_types=filtered_work_types,
                         total_payment=total_payment,
                         remaining_budget=remaining_budget,
                         work_type_codes=WORK_TYPE_CODES,
                         contractors=contractors,
                         search_code=search_code,
                         search_contractor=search_contractor,
                         site_management_cost=site_management_cost,
                         general_management_cost=general_management_cost,
                         now=datetime.now())

# 工種コードの定義
WORK_TYPE_CODES = [
    ('41-01', '準備費'),
    ('41-02', '仮設物費'),
    ('41-03', '廃棄物処分費'),
    ('41-04', '共通仮設'),
    ('41-05', '直接仮設工事'),
    ('41-90', '仮設工事一式'),
    ('42-01', '土工事'),
    ('42-02', '地業工事'),
    ('42-03', '鉄筋工事'),
    ('42-04', '型枠工事'),
    ('42-05', 'ｺﾝｸﾘｰﾄ工事'),
    ('42-06', '鉄骨工事'),
    ('42-07', '組積ALC工事'),
    ('42-08', '防水工事'),
    ('42-09', '石工事'),
    ('42-10', 'タイル工事'),
    ('42-11', '木工事'),
    ('42-12', '屋根工事'),
    ('42-13', '外装工事'),
    ('42-14', '金属工事'),
    ('42-15', '左官工事'),
    ('42-16', '木製建具工事'),
    ('42-17', '金属製建具工事'),
    ('42-18', '硝子工事'),
    ('42-19', '塗装吹付工事'),
    ('42-20', '内装工事'),
    ('42-21', '家具・雑工事'),
    ('42-22', '仮設事務所工事'),
    ('42-23', 'プール工事'),
    ('42-24', 'サイン工事'),
    ('42-25', '厨房機器工事'),
    ('42-26', '既存改修工事'),
    ('42-27', '特殊付帯工事'),
    ('42-28', '住宅設備工事'),
    ('42-29', '雑工事'),
    ('42-90', '建築工事一式'),
    ('43-01', '解体工事'),
    ('43-02', '外構開発工事'),
    ('43-03', '附帯建物工事'),
    ('43-04', '別途外構工事'),
    ('43-05', '山留工事'),
    ('43-06', '杭工事'),
    ('43-90', '解体外構附帯工事一式'),
    ('44-01', '電気設備工事'),
    ('44-02', '給排水衛生設備工事'),
    ('44-03', '空調換気設備工事'),
    ('44-04', '浄化槽工事'),
    ('44-05', '昇降機工事'),
    ('44-06', 'オイル配管設備工事'),
    ('44-07', '厨房機器工事'),
    ('44-08', 'ガス設備工事'),
    ('44-09', '消防設備工事'),
    ('44-90', '設備工事一式'),
    ('44-91', '諸経費'),
    ('45-01', '追加変更工事'),
    ('45-02', '追加変更工事２'),
    ('45-10', 'その他工事'),
    ('45-90', '追加変更一式'),
    ('46-01', '建築一式工事'),
    ('46-02', '許認可代顔料'),
    ('46-10', 'その他工事'),
    ('61-01', '管理給与'),
    ('61-02', '共通給与'),
    ('61-03', '舗装給与'),
    ('61-04', '建設業退職金共済掛金'),
    ('61-06', '油脂費'),
    ('61-10', '法定福利費（労災保険）'),
    ('61-15', '事務用品費'),
    ('61-16', '通信交通費'),
    ('61-18', '租税公課（印紙）'),
    ('61-20', '保険料（工事保険）'),
    ('61-22', '福利厚生費（被服・薬品）'),
    ('61-25', '設計費（施工図費）'),
    ('61-30', '雑費（打ち合わせ・式典）'),
]

@app.route('/add_work_type/<int:project_id>', methods=['GET', 'POST'])
def add_work_type(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        work_type = WorkType(
            project_id=project_id,
            work_code=request.form['work_code'],
            work_name=request.form['work_name'],
            budget_amount=int(request.form['budget_amount']),
            remaining_amount=int(request.form['budget_amount'])
        )
        db.session.add(work_type)
        db.session.commit()
        flash('工種を追加しました')
        return redirect(url_for('work_type_list', project_id=project_id))
    
    return render_template('add_work_type.html', 
                         project=project,
                         work_type_codes=WORK_TYPE_CODES)  # 工種コードリストを渡す

@app.route('/work_type/<int:id>/edit', methods=['GET', 'POST'])
def edit_work_type(id):
    work_type = WorkType.query.get_or_404(id)
    
    if request.method == 'POST':
        work_type.work_code = request.form['work_code']
        work_type.work_name = request.form['work_name']
        work_type.budget_amount = request.form['budget_amount']
        work_type.remaining_amount = request.form['remaining_amount']
        
        db.session.commit()
        flash('工種が正常に更新されました。')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    return render_template('edit_work_type.html', work_type=work_type)

@app.route('/payment/<int:work_type_id>', methods=['GET', 'POST'])
def payment(work_type_id):
    work_type = WorkType.query.get_or_404(work_type_id)
    
    # 年の選択肢を生成（現在年から5年分 + 未定）
    current_year = datetime.now().year
    years = [(str(year), str(year)) for year in range(current_year - 2, current_year + 4)]
    years.append(('undecided', '未定'))
    
    # 月の選択肢を生成（1-12月 + 未定）
    months = [(str(month), f"{month}月") for month in range(1, 13)]
    months.append(('undecided', '未定'))
    
    if request.method == 'POST':
        # 年と月の処理
        year = request.form['year']
        month = request.form['month']
        
        # 未定の場合は0を設定
        year = 0 if year == 'undecided' else int(year)
        month = 0 if year == 0 or month == 'undecided' else int(month)
        
        payment = Payment(
            work_type_id=work_type_id,
            year=year,
            month=month,
            contractor=request.form['contractor'],
            description=request.form['description'],
            payment_type=request.form['payment_type'],
            amount=int(request.form['amount']),
            is_progress_payment=request.form['payment_type'] == '出来高'  # 出来高払いフラグを設定
        )
        
        # 出来高払いの場合、進捗率を設定
        if payment.is_progress_payment:
            payment.progress_rate = float(request.form.get('progress_rate', 0))
            payment.current_progress = payment.progress_rate
            
            # 前回までの出来高を取得
            previous_payments = Payment.query.filter(
                Payment.work_type_id == work_type_id,
                Payment.is_progress_payment == True
            ).order_by(Payment.id.desc()).first()
            
            payment.previous_progress = previous_payments.current_progress if previous_payments else 0
        
        db.session.add(payment)
        db.session.commit()
        
        # 工種の残額を再計算
        work_type.calculate_remaining_amount()
        db.session.commit()
        
        flash('支払い情報を登録しました')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
        
    return render_template('payment.html', 
                         work_type=work_type,
                         years=years,
                         months=months)

@app.route('/api/payment_history/<int:work_type_id>')
def payment_history(work_type_id):
    payments = Payment.query.filter_by(work_type_id=work_type_id)\
        .order_by(Payment.year.desc(), Payment.month.desc())\
        .all()
    return jsonify({
        'payments': [{
            'id': payment.id,
            'payment_date': "未定" if payment.year == 0 else f"{payment.year}年{payment.month if payment.month != 0 else '未定'}月",
            'contractor': payment.contractor,
            'amount': f"¥{payment.amount:,}",
            'description': payment.description,
            'payment_type': payment.payment_type
        } for payment in payments]
    })

@app.route('/edit_payment/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    work_type = payment.work_type
    
    if request.method == 'POST':
        try:
            # 既存の処理
            year = request.form.get('year')
            month = request.form.get('month')
            amount = request.form.get('amount')
            
            payment.year = int(year) if year else 0
            payment.month = int(month) if month else 0
            payment.amount = int(float(amount)) if amount else 0
            
            payment.contractor = request.form.get('contractor')
            payment.description = request.form.get('description')
            payment.payment_type = request.form.get('payment_type')
            
            # 出来高払い関連の処理を追加
            payment.is_progress_payment = 'is_progress_payment' in request.form
            if payment.is_progress_payment:
                payment.progress_rate = float(request.form.get('progress_rate', 0))
                payment.current_progress = payment.progress_rate
                
                # 前回までの出来高を取得
                previous_payments = Payment.query.filter(
                    Payment.work_type_id == work_type.id,
                    Payment.is_progress_payment == True,
                    Payment.id < payment_id
                ).order_by(Payment.id.desc()).first()
                
                payment.previous_progress = previous_payments.progress_rate if previous_payments else 0
            
            # 残額を再計算
            work_type.remaining_amount = work_type.calculate_remaining_amount()
            
            db.session.commit()
            flash('支払い情報を更新しました')
            return redirect(url_for('work_type_list', project_id=work_type.project_id))
            
        except (ValueError, TypeError) as e:
            db.session.rollback()
            flash('入力データが不正です。金額は正しい数値を入力してください。')
            return redirect(url_for('edit_payment', payment_id=payment_id))
            
    return render_template('edit_payment.html', payment=payment)

@app.route('/delete_project/<int:id>', methods=['POST'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    flash('物件が削除されました')
    return redirect(url_for('index'))

@app.route('/delete_work_type/<int:id>', methods=['POST'])
def delete_work_type(id):
    work_type = WorkType.query.get_or_404(id)
    project_id = work_type.project_id
    db.session.delete(work_type)
    db.session.commit()
    flash('工種が削除されました')
    return redirect(url_for('work_type_list', project_id=project_id))

@app.route('/delete_payment/<int:id>', methods=['POST'])
def delete_payment(id):
    payment = Payment.query.get_or_404(id)
    project_id = payment.work_type.project_id
    db.session.delete(payment)
    db.session.commit()
    flash('支払い情報が削除されました')
    return redirect(url_for('work_type_list', project_id=project_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            
            if not username or not password:
                flash('ユーザー名とパスワードを入力してください')
                return redirect(url_for('login'))
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(password):
                # セッションを永続化
                session.permanent = True
                # ユーザーをログイン
                login_user(user, remember=True)
                flash('ログインしました')
                
                # next_pageの取得とバリデーション
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('index')
                return redirect(next_page)
            
            flash('ユーザー名またはパスワードが正しくありません')
            return redirect(url_for('login'))
            
        except Exception as e:
            print(f"ログインエラー: {str(e)}")
            flash('ログイン中にエラーが発生しました')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            # 必須フィールドの確認
            if not all([
                request.form.get('username'),
                request.form.get('email'),
                request.form.get('password')
            ]):
                flash('すべての項目を入力してください')
                return redirect(url_for('register'))

            # 既存ユーザーチェック
            if User.query.filter_by(username=request.form['username']).first():
                flash('このユーザー名は既に使用されています')
                return redirect(url_for('register'))
            if User.query.filter_by(email=request.form['email']).first():
                flash('このメールアドレスは既に使用されています')
                return redirect(url_for('register'))
            
            # 新規ユーザー作成
            user = User(
                username=request.form['username'],
                email=request.form['email']
            )
            user.set_password(request.form['password'])
            
            # データベースに保存
            with app.app_context():
                db.session.add(user)
                db.session.commit()
            
            flash('ユーザー登録が完了しました')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            print(f"登録エラー: {str(e)}")  # エラーの詳細をログに出力
            flash('登録中にエラーが発生しました')
            return redirect(url_for('register'))
            
    return render_template('register.html')

@app.route('/users')
@login_required
def user_list():
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です')
        return redirect(url_for('index'))
    users = User.query.all()
    return render_template('user_list.html', users=users)

@app.route('/edit_user/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if not current_user.is_admin and current_user.id != id:
        flash('この操作は許可されていません')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        if current_user.is_admin:
            user.username = request.form['username']
            user.email = request.form['email']
            user.is_admin = 'is_admin' in request.form
        if request.form.get('password'):
            user.set_password(request.form['password'])
        db.session.commit()
        flash('ユーザー情報を更新しました')
        return redirect(url_for('user_list' if current_user.is_admin else 'index'))
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    if not current_user.is_admin:
        flash('この操作には管理者権限が必要です')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash('自分自身は削除できません')
        return redirect(url_for('user_list'))
    
    db.session.delete(user)
    db.session.commit()
    flash('ユーザーを削除しました')
    return redirect(url_for('user_list'))

@app.route('/work_type/<int:work_type_id>/progress_payment', methods=['GET', 'POST'])
def progress_payment(work_type_id):
    work_type = WorkType.query.get_or_404(work_type_id)
    
    # リクエストから請負契約IDを取得
    contract_id = request.args.get('contract_id')
    if not contract_id:
        flash('請負契約が指定されていません')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    # 指定された請負契約を取得
    contract_payment = Payment.query.get_or_404(contract_id)
    if contract_payment.work_type_id != work_type_id or contract_payment.payment_type != '請負':
        flash('無効な請負契約です')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    # この請負契約に関連する出来高支払いを取得
    progress_payments = Payment.query.filter_by(
        work_type_id=work_type_id,
        payment_type='出来高',
        contractor=contract_payment.contractor,
        contract_id=contract_payment.id  # 請負契約IDでフィルタリング
    ).order_by(Payment.year.desc(), Payment.month.desc()).all()
    
    # 前回までの出来高を取得
    last_progress = progress_payments[0] if progress_payments else None
    previous_progress = last_progress.current_progress if last_progress else 0
    
    # 出来高支払い合計額を計算
    total_progress_amount = sum(payment.amount for payment in progress_payments)
    
    if request.method == 'POST':
        amount = int(request.form['amount'])
        progress_rate = (amount / contract_payment.amount) * 100
        
        payment = Payment(
            work_type_id=work_type_id,
            year=int(request.form['year']),
            month=int(request.form['month']),
            contractor=contract_payment.contractor,
            description=request.form['description'],
            payment_type='出来高',
            amount=amount,
            is_progress_payment=True,
            progress_rate=progress_rate,
            previous_progress=previous_progress,
            current_progress=previous_progress + progress_rate,
            contract_id=contract_payment.id  # 請負契約IDを保存
        )
        
        db.session.add(payment)
        work_type.calculate_remaining_amount()
        db.session.commit()
        
        flash('出来高払いを登録しました')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    return render_template('progress_payment.html', 
                         work_type=work_type,
                         contract_payment=contract_payment,
                         previous_progress=previous_progress,
                         total_progress_amount=total_progress_amount,
                         current_year=datetime.now().year)

@app.route('/work_type/<int:work_type_id>/profit', methods=['GET', 'POST'])
def profit_entry(work_type_id):
    work_type = WorkType.query.get_or_404(work_type_id)
    
    if request.method == 'POST':
        # 利益計上として支払いを登録
        payment = Payment(
            work_type_id=work_type_id,
            year=datetime.now().year,  # 現在の年を設定
            month=datetime.now().month,  # 現在の月を設定
            contractor='利益計上',
            description=request.form['description'],
            payment_type='利益計上',
            amount=int(request.form['amount']),
            is_profit=True
        )
        
        db.session.add(payment)
        work_type.calculate_remaining_amount()
        db.session.commit()
        
        flash('利益計上を登録しました')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    return render_template('profit_entry.html', work_type=work_type)

@app.route('/work_type/<int:work_type_id>/profit/edit', methods=['GET', 'POST'])
def edit_profit(work_type_id):
    work_type = WorkType.query.get_or_404(work_type_id)
    
    # 利益計上の支払いを取得
    profit_payment = Payment.query.filter_by(
        work_type_id=work_type_id,
        is_profit=True
    ).first()
    
    if not profit_payment:
        flash('利益計上データが見つかりません')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    if request.method == 'POST':
        profit_payment.amount = int(request.form['amount'])
        profit_payment.description = request.form['description']
        
        db.session.commit()
        work_type.calculate_remaining_amount()
        db.session.commit()
        
        flash('利益計上を更新しました')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
    
    return render_template('edit_profit.html', 
                         work_type=work_type,
                         profit_payment=profit_payment)

@app.route('/projects/<int:project_id>/target_management', methods=['GET', 'POST'])
def set_target_management(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        project.target_management_rate = float(request.form['target_rate'])
        db.session.commit()
        flash('目標一般管理費率を設定しました')
        return redirect(url_for('work_type_list', project_id=project.id))
    
    return render_template('set_target_management.html', project=project)

@app.cli.command('reset-db')
def reset_db():
    """データベースを完全にリセットする"""
    # MySQLに直接接続してデータベースを再作成
    engine = create_engine('mysql+pymysql://root:kikuoo@localhost/')
    conn = engine.connect()
    
    try:
        # トランザクションをコミット
        conn.execute(text('COMMIT'))
        
        # データベースを削除して再作成
        conn.execute(text('DROP DATABASE IF EXISTS yosan_db'))
        conn.execute(text('CREATE DATABASE yosan_db'))
    finally:
        conn.close()
    
    # テーブルを再作成
    db.create_all()
    
    # マイグレーションフォルダがある場合は削除して再初期化
    if os.path.exists('migrations'):
        shutil.rmtree('migrations')
    
    # マイグレーションを初期化
    os.system('flask db init')
    os.system('flask db migrate -m "Initial migration"')
    os.system('flask db upgrade')
    
    print('Database has been reset successfully.')

@app.route('/init_db')
def initialize_database():
    try:
        with app.app_context():
            db.create_all()
            
            # 初期管理者ユーザーの作成
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    is_admin=True
                )
                admin.set_password('initial_password')
                db.session.add(admin)
                db.session.commit()
            
            return 'データベースが初期化されました'
    except Exception as e:
        return f'エラーが発生しました: {str(e)}'

if __name__ == '__main__':
    app.run(debug=True) 