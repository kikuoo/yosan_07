from app import db
from app import User
from werkzeug.security import generate_password_hash

def init_db():
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

if __name__ == '__main__':
    init_db() 