from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timezone
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLAlchemy設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kikuoo@localhost/yosan_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'ログインしてください。'

# モデル定義
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(50), nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    contract_amount = db.Column(db.Integer, nullable=False)
    budget_amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    # 関連する工種が削除されるように設定
    work_types = db.relationship('WorkType', backref='project', lazy=True, cascade='all, delete-orphan')

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
@login_required
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project = Project(
            project_code=request.form['project_code'],
            project_name=request.form['project_name'],
            contract_amount=int(request.form['contract_amount']),
            budget_amount=int(request.form['budget_amount'])
        )
        db.session.add(project)
        db.session.commit()
        flash('物件が正常に追加されました.')
        return redirect(url_for('index'))
    
    return render_template('add_project.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_project(id):
    project = Project.query.get_or_404(id)
    
    if request.method == 'POST':
        project.project_code = request.form['project_code']
        project.project_name = request.form['project_name']
        project.contract_amount = request.form['contract_amount']
        project.budget_amount = request.form['budget_amount']
        
        db.session.commit()
        flash('物件が正常に更新されました')
        return redirect(url_for('index'))
    
    return render_template('edit_project.html', project=project)

@app.route('/project/<int:project_id>/work_types')
def work_type_list(project_id):
    project = Project.query.get_or_404(project_id)
    work_types = WorkType.query.filter_by(project_id=project_id).order_by(WorkType.work_code).all()
    return render_template('work_type_list.html', project=project, work_types=work_types)

@app.route('/project/<int:project_id>/work_types/add', methods=['GET', 'POST'])
def add_work_type(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        work_type = WorkType(
            project_id=project_id,
            work_code=request.form['work_code'],
            work_name=request.form['work_name'],
            budget_amount=request.form['budget_amount'],
            remaining_amount=request.form['budget_amount']  # 初期値は予算額と同じ
        )
        db.session.add(work_type)
        db.session.commit()
        flash('工種が正常に追加されました。')
        return redirect(url_for('work_type_list', project_id=project_id))
    
    return render_template('add_work_type.html', project=project)

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
    
    if request.method == 'POST':
        payment = Payment(
            work_type_id=work_type_id,
            year=request.form['year'],
            month=request.form['month'],
            contractor=request.form['contractor'],
            description=request.form['description'],
            payment_type=request.form['payment_type'],
            amount=request.form['amount']
        )
        db.session.add(payment)
        db.session.commit()
        flash('支払い情報を登録しました')
        return redirect(url_for('work_type_list', project_id=work_type.project_id))
        
    return render_template('payment.html', work_type=work_type)

@app.route('/api/payment_history/<int:work_type_id>')
def payment_history(work_type_id):
    payments = Payment.query.filter_by(work_type_id=work_type_id)\
        .order_by(Payment.year.desc(), Payment.month.desc())\
        .all()
    return jsonify({
        'payments': [{
            'id': payment.id,
            'payment_date': f"{payment.year}年{payment.month}月",
            'contractor': payment.contractor,
            'amount': f"¥{payment.amount:,}",
            'description': payment.description,
            'payment_type': payment.payment_type
        } for payment in payments]
    })

@app.route('/edit_payment/<int:payment_id>', methods=['GET', 'POST'])
def edit_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    if request.method == 'POST':
        payment.year = int(request.form['year'])
        payment.month = int(request.form['month'])
        payment.contractor = request.form['contractor']
        payment.description = request.form['description']
        payment.payment_type = request.form['payment_type']
        payment.amount = int(request.form['amount'])
        db.session.commit()
        return redirect(url_for('work_type_list', project_id=payment.work_type.project_id))
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
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('ユーザー名またはパスワードが正しくありません')
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

if __name__ == '__main__':
    app.run(debug=True) 