from app import create_app, db
from app.models import User, Property, ConstructionBudget
from flask_migrate import upgrade, Migrate
import os
from dotenv import load_dotenv

load_dotenv()

app = create_app()

def init_database():
    with app.app_context():
        try:
            # データベースのマイグレーションを実行
            upgrade()
            print('データベースのマイグレーションを実行しました')
        except Exception as e:
            print(f'マイグレーションエラー: {str(e)}')
            # エラーが発生した場合は、テーブルを直接作成
            db.create_all()
            print('テーブルを直接作成しました')
        
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

# アプリケーション起動時にデータベースを初期化
init_database()

if __name__ == '__main__':
    app.run(debug=True)