from app import app, db, User
from sqlalchemy import inspect

def init_database():
    """データベースの初期化とテーブルの作成を行う"""
    try:
        with app.app_context():
            # テーブルが存在するか確認
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # 本番環境では既存のテーブルがある場合は何もしない
            if existing_tables:
                print("既存のデータベースを保持します")
                return
            
            # テーブルが存在しない場合のみ新規作成
            print("新規データベースを作成します")
            db.create_all()
            
            # 管理者ユーザーが存在しない場合のみ作成
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
    except Exception as e:
        print(f"データベース初期化エラー: {str(e)}")

# アプリケーション起動時にデータベースを初期化
init_database()

if __name__ == "__main__":
    app.run() 