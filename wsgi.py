from app import app, db, User
from sqlalchemy import inspect

# アプリケーション起動時にデータベースのテーブル存在確認
with app.app_context():
    try:
        # データベースインスペクターを作成
        inspector = inspect(db.engine)
        
        # 必要なテーブルが存在するか確認
        required_tables = {'users', 'projects', 'work_types', 'payments'}
        existing_tables = set(inspector.get_table_names())
        
        if not required_tables.issubset(existing_tables):
            # 必要なテーブルが存在しない場合、データベースを初期化
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
            print("データベースを新規作成しました")
        else:
            print("既存のデータベースを使用します")
    except Exception as e:
        print(f"データベース初期化エラー: {str(e)}")

if __name__ == "__main__":
    app.run() 