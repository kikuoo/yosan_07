from app import db, app, User
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
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

if __name__ == '__main__':
    init_db() 