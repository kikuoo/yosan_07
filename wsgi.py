from app import create_app, db
from app.models import User, Property, ConstructionBudget
import os
from dotenv import load_dotenv
from sqlalchemy import text
        
load_dotenv()

# アプリケーションの作成
app = create_app()

def init_database():
    with app.app_context():
        try:
            # テーブルを作成
            db.create_all()
            print('テーブルを作成しました')

            # テーブルが正しく作成されたか確認
            db.session.execute(text('SELECT 1 FROM property LIMIT 1'))
            print('propertyテーブルが存在することを確認しました')
        except Exception as e:
            print(f'テーブル作成エラー: {str(e)}')
            try:
                # テーブルを個別に作成
                db.session.execute(text('''
                    CREATE TABLE IF NOT EXISTS "user" (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(80) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(512),
                        is_admin BOOLEAN DEFAULT FALSE
                    )
                '''))
                
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
                print(f'個別テーブル作成エラー: {str(e)}')
                db.session.rollback()
        
        try:
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
        except Exception as e:
            print(f'管理者ユーザー作成エラー: {str(e)}')
            db.session.rollback()

# アプリケーション起動時にデータベースを初期化
init_database()

# Gunicorn用のアプリケーションエクスポート
application = app

if __name__ == '__main__':
    # ローカル開発環境用
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # Render環境用
    app = application