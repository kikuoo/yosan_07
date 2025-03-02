from app import db, User

def seed_database():
    # データベースの初期化
    db.create_all()
    
    # 初期ユーザーの作成
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            email='admin@example.com',
            username='admin',
            is_admin=True
        )
        admin.set_password('initial_password')  # User modelのメソッドを使用
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    seed_database()