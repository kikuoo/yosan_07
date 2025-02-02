from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# SQLAlchemy設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:kikuoo@localhost/yosan_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# モデル定義
class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    project_code = db.Column(db.String(50), nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    contract_amount = db.Column(db.Numeric(12, 0), nullable=False)
    budget_amount = db.Column(db.Numeric(12, 0), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

class WorkType(db.Model):
    __tablename__ = 'work_types'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    work_code = db.Column(db.String(50), nullable=False)
    work_name = db.Column(db.String(200), nullable=False)
    budget_amount = db.Column(db.Numeric(12, 0), nullable=False)
    remaining_amount = db.Column(db.Numeric(12, 0), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    project = db.relationship('Project', backref=db.backref('work_types', lazy=True))

@app.route('/')
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('index.html', projects=projects)

@app.route('/add', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        project = project(
            project_code=request.form['project_code'],#プロジェクトコード
            project_name=request.form['project_name'],#プロジェクト名
            contract_amount=request.form['contract_amount'],#契約金額
            budget_amount=request.form['budget_amount']#予算金額
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 