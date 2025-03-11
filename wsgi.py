from app import app
from app import db
from sqlalchemy import text
import os
from urllib.parse import urlparse
from sqlalchemy import create_engine
import time

# アプリケーション起動時にデータベースを初期化
def check_database_connection():
    """データベース接続を確認する関数"""
    from app import db
    import os
    
    try:
        # データベースURLを取得
        database_url = os.getenv('DATABASE_URL', 'unknown')
        if database_url:
            # 改行文字を削除し、空白を削除
            database_url = ''.join(database_url.strip().split())
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

        # 改行文字と空白を完全に削除
        database_url = ''.join(database_url.strip().split())
        
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # URLをパース
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip('/').strip()  # データベース名から空白と改行を削除
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        print(f"データベース名: [{db_name}]")
        print(f"ベースURL: {base_url}")
        
        # まずpostgresデータベースに接続
        postgres_url = f"{base_url}/postgres"
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        try:
            # データベースが存在するか確認
            with engine.connect() as conn:
                # データベース名をエスケープ
                escaped_db_name = db_name.replace("'", "''")
                result = conn.execute(text(
                    f"SELECT 1 FROM pg_database WHERE datname = '{escaped_db_name}'"
                ))
                exists = result.scalar() is not None
                
                if not exists:
                    print(f"データベース {db_name} が存在しないため、作成します")
                    # 既存の接続を全て切断
                    conn.execute(text(f"""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = '{escaped_db_name}'
                    """))
                    # データベースを作成
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    print(f"データベース {db_name} を作成しました")
                else:
                    print(f"データベース {db_name} は既に存在します")
                    # 既存の接続を全て切断
                    conn.execute(text(f"""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = '{escaped_db_name}'
                        AND pid <> pg_backend_pid()
                    """))
                
                # データベースが本当に存在するか確認
                check_query = text(f'SELECT 1 FROM pg_database WHERE datname = :db_name')
                result = conn.execute(check_query, {'db_name': db_name})
                if not result.scalar():
                    raise Exception(f"データベース {db_name} の作成を確認できません")
                
        except Exception as e:
            print(f"データベース作成エラー: {str(e)}")
            raise

        # 少し待機してデータベースの作成が完了するのを待つ
        time.sleep(5)

        # アプリケーションのデータベースに接続
        app_engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30
        )
        
        # 接続を確立するまで複数回試行
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                # 接続テスト
                with app_engine.connect() as conn:
                    # テーブルの存在確認
                    result = conn.execute(text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE'
                    """))
                    tables = [row[0] for row in result]
                    print(f"存在するテーブル: {tables}")
                    
                    if not tables:
                        print("テーブルが存在しないため、作成します")
                        with app.app_context():
                            db.create_all()
                            db.session.commit()
                        print("テーブルを作成しました")
                    else:
                        print("テーブルは既に存在します")
                    
                    print("データベース接続テスト成功")
                    break  # 成功したらループを抜ける
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                print(f"接続試行 {retry_count}/{max_retries} 失敗: {str(e)}")
                time.sleep(2)  # 再試行前に待機
                
        if retry_count >= max_retries:
            print(f"データベース接続テストエラー: {str(last_error)}")
            raise last_error

        with app.app_context():
            try:
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
                db.session.rollback()
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