from app import app, db, User

def create_admin_user():
    with app.app_context():
        # 管理者ユーザーが存在するか確認
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')  # 初期パスワード
            db.session.add(admin)
            db.session.commit()
            print('管理者ユーザーを作成しました')
        else:
            print('管理者ユーザーは既に存在します')

if __name__ == '__main__':
    create_admin_user() 