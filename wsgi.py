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
        
        with app.app_context():
            # テーブルのスキーマを確認
            try:
                result = db.session.execute(text("""
                    SELECT column_name, character_maximum_length 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'password_hash'
                """))
                column_info = result.fetchone()
                
                # password_hashカラムの長さが512未満の場合、テーブルを再作成
                if not column_info or column_info[1] < 512:
                    print("テーブルのスキーマを更新します")
                    db.session.execute(text('DROP TABLE IF EXISTS "user" CASCADE'))
                    db.session.commit()
                    db.create_all()
                    print("テーブルを再作成しました")
            except Exception as e:
                print(f"テーブルスキーマの確認中にエラーが発生しました: {str(e)}")
                db.create_all()
                print("テーブルを作成しました")

            try:
                # 管理者ユーザーの確認と作成
                from app.models import User
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
                import traceback
                print(f"スタックトレース: {traceback.format_exc()}")
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