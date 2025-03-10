from app import app
from app import db
from sqlalchemy import text
import os

# アプリケーション起動時にデータベースを初期化
def check_database_connection():
    """データベース接続を確認する関数"""
    from app import db
    import os
    
    try:
        # データベースURLを取得
        database_url = os.getenv('DATABASE_URL', 'unknown')
        if database_url:
            # 改行文字を削除
            database_url = database_url.strip()
            print(f"データベースURL: {database_url.split('@')[1] if '@' in database_url else database_url}")
        
        with app.app_context():
            # 接続テスト
            db.engine.dispose()  # 既存の接続を破棄
            db.session.remove()  # セッションをクリア
            
            # 接続テスト用のシンプルなクエリを実行
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            
            print("データベース接続成功")
            return True
    except Exception as e:
        print(f"データベース接続エラー: {str(e)}")
        import traceback
        print(f"スタックトレース: {traceback.format_exc()}")
        return False

def init_database():
    """データベースの初期化とテーブルの作成を行う"""
    try:
        # まず接続を確認
        if not check_database_connection():
            print("データベース接続に失敗しました。データベースの作成を試みます...")
            
            # データベースURLから接続情報を取得
            database_url = os.getenv('DATABASE_URL', '')
            if database_url:
                # 改行文字を削除
                database_url = database_url.strip()
                
                if database_url.startswith("postgres://"):
                    database_url = database_url.replace("postgres://", "postgresql://", 1)
                
                # データベース名を取得（改行文字を削除）
                db_name = database_url.split('/')[-1].strip()
                base_url = database_url.rsplit('/', 1)[0]
                
                print(f"データベース名: {db_name}")
                print(f"ベースURL: {base_url}")
                
                # デフォルトのデータベースに接続して新しいデータベースを作成
                from sqlalchemy import create_engine
                engine = create_engine(base_url + '/postgres')
                with engine.connect() as conn:
                    conn.execute(text('commit'))
                    conn.execute(text(f'CREATE DATABASE {db_name}'))
                    conn.execute(text('commit'))
                
                print(f"データベース {db_name} を作成しました")
                
                # 接続を再試行
                if not check_database_connection():
                    raise Exception("データベースの作成に失敗しました")

        from app import app, db, User
        
        with app.app_context():
            try:
                # テーブルの存在確認をより詳細に行う
                print("テーブルの存在確認を開始します...")
                
                # PostgreSQL用のテーブル一覧取得
                result = db.session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """))
                tables = [row[0] for row in result]
                print(f"存在するテーブル: {tables}")
                
                # usersテーブルの存在を確認
                if 'users' in tables:
                    user_count = User.query.count()
                    print(f"既存のユーザー数: {user_count}")
                    if user_count > 0:
                        print("既存のデータベースとユーザーが存在します。初期化をスキップします。")
                        return
                else:
                    print("usersテーブルが存在しません")
                    
            except Exception as e:
                print(f"テーブル確認エラー（新規作成を実行します）: {str(e)}")
                print(f"エラーの詳細: {type(e).__name__}")
                import traceback
                print(f"スタックトレース: {traceback.format_exc()}")
                table_exists = False

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
        import traceback
        print(f"スタックトレース: {traceback.format_exc()}")
        raise

# アプリケーション起動時にデータベースを初期化
with app.app_context():
    init_database()

if __name__ == "__main__":
    app.run()