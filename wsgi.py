from app import app, db, User
from sqlalchemy import inspect, text
import os

def check_database_connection():
    """データベース接続を確認する"""
    try:
        with app.app_context():
            # データベースURLの確認
            database_url = os.getenv('DATABASE_URL', 'Not Set')
            if not database_url.startswith('postgresql://'):
                raise Exception("PostgreSQLの接続URLが正しく設定されていません")

            # 接続テスト用のシンプルなクエリを実行
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            # URLの機密情報を隠す
            safe_url = database_url.split('@')[1] if '@' in database_url else database_url
            print(f"データベース接続成功: {safe_url}")
            return True
    except Exception as e:
        print(f"データベース接続エラー: {str(e)}")
        return False

def init_database():
    """データベースの初期化とテーブルの作成を行う"""
    try:
        # まず接続を確認
        if not check_database_connection():
            raise Exception("データベースに接続できません")

        with app.app_context():
            # テーブルの存在確認
            try:
                # PostgreSQL用のシンプルなクエリに変更
                result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM pg_tables 
                        WHERE schemaname = 'public' 
                        AND tablename = 'users'
                    )
                """))
                table_exists = result.scalar()
                
                if table_exists:
                    user_count = User.query.count()
                    print(f"既存のユーザー数: {user_count}")
                    if user_count > 0:
                        print("既存のデータベースとユーザーが存在します。初期化をスキップします。")
                        return
            except Exception as e:
                print(f"テーブル確認エラー: {str(e)}")

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
        raise

# アプリケーション起動時にデータベースを初期化
init_database()

if __name__ == "__main__":
    app.run() 