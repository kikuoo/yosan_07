from app import db, User
from werkzeug.security import generate_password_hash

def seed_database():
    # データベースの初期化
    db.create_all()
    
    # 初期ユーザーの作成
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            email='admin@example.com',
            password=generate_password_hash('your-password'),
            # その他必要なフィールド
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    seed_database()