from app import app
from app import db
from sqlalchemy import text
import os
from urllib.parse import urlparse
from sqlalchemy import create_engine

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
        # データベースURLから接続情報を取得
        database_url = os.getenv('DATABASE_URL', '')
        if not database_url:
            raise Exception("DATABASE_URL が設定されていません")

        # 改行文字を削除し、URLを正規化
        database_url = database_url.strip().replace('\n', '').replace('\r', '')
        
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # URLをパース
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip('/').strip().replace('\n', '').replace('\r', '')
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        print(f"データベース名: [{db_name}]")  # 角括弧で囲んで表示
        print(f"ベースURL: {base_url}")
        
        # まずpostgresデータベースに接続
        postgres_url = f"{base_url}/postgres"
        engine = create_engine(postgres_url)
        
        try:
            # データベースが存在するか確認
            with engine.connect() as conn:
                # トランザクションをコミット
                conn.execute(text("commit"))
                
                # データベースの存在確認（エスケープ処理を追加）
                escaped_db_name = db_name.replace("'", "''")
                result = conn.execute(text(
                    f"SELECT 1 FROM pg_database WHERE datname = '{escaped_db_name}'"
                ))
                exists = result.scalar() is not None
                
                if not exists:
                    print(f"データベース {db_name} が存在しないため、作成します")
                    # 新しいトランザクションを開始
                    conn.execute(text("commit"))
                    # データベース名をダブルクォートで囲む
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    conn.execute(text("commit"))
                    print(f"データベース {db_name} を作成しました")
                else:
                    print(f"データベース {db_name} は既に存在します")
                    
                # データベースが本当に存在するか確認
                check_query = text(f'SELECT 1 FROM pg_database WHERE datname = :db_name')
                result = conn.execute(check_query, {'db_name': db_name})
                if not result.scalar():
                    raise Exception(f"データベース {db_name} の作成を確認できません")
                
        except Exception as e:
            print(f"データベース作成エラー: {str(e)}")
            raise

        # アプリケーションのデータベースに接続
        app_engine = create_engine(database_url)
        try:
            # 接続テスト
            with app_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("データベース接続テスト成功")
        except Exception as e:
            print(f"データベース接続テストエラー: {str(e)}")
            raise

        with app.app_context():
            try:
                # テーブルの存在確認
                print("テーブルの存在確認を開始します...")
                result = db.session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """))
                tables = [row[0] for row in result]
                print(f"存在するテーブル: {tables}")
                
                if not tables:
                    print("テーブルが存在しないため、作成します")
                    db.create_all()
                    print("テーブルを作成しました")
                
                # 管理者ユーザーの確認と作成
                from app import User
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
                    print("管理者ユーザーは既に存在します")
                
            except Exception as e:
                print(f"テーブル初期化エラー: {str(e)}")
                raise
            
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