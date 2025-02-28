from app import app, db, User
from sqlalchemy import inspect

def init_database():
    """データベースの初期化とテーブルの作成を行う"""
    try:
        # データベースインスペクターを作成
        inspector = inspect(db.engine)
        
        # 必要なテーブルが存在するか確認
        required_tables = {'users', 'projects', 'work_types', 'payments'}
        existing_tables = set(inspector.get_table_names())
        
        if not required_tables.issubset(existing_tables):
            print("必要なテーブルが存在しません。データベースを初期化します...")
            # テーブルを作成
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
                print("管理者ユーザーを作成しました")
            
            print("データベースの初期化が完了しました")
        else:
            print("既存のデータベースを使用します")
            
    except Exception as e:
        print(f"データベース初期化エラー: {str(e)}")
        raise e

# アプリケーション起動時にデータベースを初期化
with app.app_context():
    init_database()

if __name__ == "__main__":
    app.run() 