from app import create_app, db
from app.models import User, Property, ConstructionBudget
from flask_migrate import upgrade, Migrate
import os
from dotenv import load_dotenv
from sqlalchemy import text

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
            try:
                # テーブルが存在しない場合は作成
                db.create_all()
                print('テーブルを直接作成しました')
            except Exception as e:
                print(f'テーブル作成エラー: {str(e)}')
                # エラーが発生した場合は、テーブルを個別に作成
                try:
                    # propertyテーブルの作成
                    db.session.execute(text('''
                        CREATE TABLE IF NOT EXISTS property (
                            id SERIAL PRIMARY KEY,
                            code VARCHAR(20) UNIQUE NOT NULL,
                            name VARCHAR(200) NOT NULL,
                            contract_amount INTEGER NOT NULL,
                            budget_amount INTEGER NOT NULL,
                            user_id INTEGER NOT NULL REFERENCES "user"(id),
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    # construction_budgetテーブルの作成
                    db.session.execute(text('''
                        CREATE TABLE IF NOT EXISTS construction_budget (
                            id SERIAL PRIMARY KEY,
                            code VARCHAR(20) NOT NULL,
                            name VARCHAR(200) NOT NULL,
                            amount INTEGER NOT NULL,
                            property_id INTEGER NOT NULL REFERENCES property(id),
                            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        )
                    '''))
                    db.session.commit()
                    print('テーブルを個別に作成しました')
                except Exception as e:
                    print(f'テーブル作成エラー: {str(e)}')
                    db.session.rollback()
        
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