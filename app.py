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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 