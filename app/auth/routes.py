from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
from app import db

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 入力値の検証
        if not username or not email or not password or not confirm_password:
            flash('すべての項目を入力してください')
            return render_template('register.html')

        if password != confirm_password:
            flash('パスワードが一致しません')
            return render_template('register.html')

        # ユーザー名とメールアドレスの重複チェック
        if User.query.filter_by(username=username).first():
            flash('このユーザー名は既に使用されています')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に使用されています')
            return render_template('register.html')

        # 新規ユーザーの作成
        user = User(username=username, email=email)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('登録が完了しました。ログインしてください。')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('登録中にエラーが発生しました。もう一度お試しください。')
            return render_template('register.html')

    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="utf-8">
            <title>ログイン - 予算管理システム</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body>
            <div class="container mt-5">
                <div class="row justify-content-center">
                    <div class="col-md-6">
                        <div class="card">
                            <div class="card-header">
                                <h4 class="mb-0">ログイン</h4>
                            </div>
                            <div class="card-body">
                                <form method="POST">
                                    <div class="mb-3">
                                        <label for="username" class="form-label">ユーザー名</label>
                                        <input type="text" class="form-control" id="username" name="username" required>
                                    </div>
                                    <div class="mb-3">
                                        <label for="password" class="form-label">パスワード</label>
                                        <input type="password" class="form-control" id="password" name="password" required>
                                    </div>
                                    <div class="d-grid">
                                        <button type="submit" class="btn btn-primary">ログイン</button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
    
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        flash('ユーザー名とパスワードを入力してください')
        return redirect(url_for('auth.login'))
    
    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        flash('ユーザー名またはパスワードが正しくありません')
        return redirect(url_for('auth.login'))
    
    login_user(user)
    return redirect(url_for('main.budgets'))

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index')) 