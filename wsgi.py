from app import app, db, User
from sqlalchemy import inspect, text
import os

def check_database_connection():
    """データベース接続を確認する"""
    try:
        with app.app_context():
            # 接続テスト用のシンプルなクエリを実行
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            database_url = os.getenv('DATABASE_URL', 'Not Set')
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
            # スキーマも含めてテーブルを確認
            inspector = inspect(db.engine)
            # 明示的にpublicスキーマを指定
            existing_tables = inspector.get_table_names(schema='public')
            print(f"既存のテーブル: {existing_tables}")
            
            # テーブルの存在確認を改善
            try:
                # 直接SQLクエリでテーブルの存在を確認
                result = db.session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
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
            if not table_exists:
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
        raise  # エラーを再度発生させてアプリケーションを停止

# アプリケーション起動時にデータベースを初期化
init_database()

if __name__ == "__main__":
    app.run() 