from app import create_app, db
from app.models import User, Property, ConstructionBudget
from flask_migrate import upgrade
import os
from dotenv import load_dotenv

load_dotenv()

app = create_app()

def init_database():
    with app.app_context():
        # データベースのマイグレーションを実行
        upgrade()
        
        # 管理者ユーザーの作成
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
            print('管理者ユーザーを作成しました')
        else:
            print('管理者ユーザーは既に存在します')

if __name__ == '__main__':
    init_database()
    app.run(debug=True)