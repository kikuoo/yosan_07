from app import app, db, User
from sqlalchemy import inspect

def init_database():
    """データベースの初期化とテーブルの作成を行う"""
    try:
        with app.app_context():
            # テーブルが存在するか確認
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # テーブルが存在しない場合のみ作成
            if not existing_tables:
                print("新規データベースを作成します")
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
            else:
                print("既存のデータベースが見つかりました")
    except Exception as e:
        print(f"データベース初期化エラー: {str(e)}")

# アプリケーション起動時にデータベースを初期化
init_database()

if __name__ == "__main__":
    app.run() 