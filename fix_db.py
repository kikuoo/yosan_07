from app import create_app, db
from app.models import User, Property, ConstructionBudget, Payment
import sqlite3

app = create_app()

with app.app_context():
    # テーブルを再作成
    db.drop_all()
    db.create_all()
    
    # 管理者ユーザーを作成
    admin = User(
        username='admin',
        email='admin@example.com',
        is_admin=True
    )
    admin.set_password('admin')
    db.session.add(admin)
    db.session.commit()
    
    print("データベースを再作成しました。") 