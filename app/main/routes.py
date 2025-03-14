from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Property, ConstructionBudget, CONSTRUCTION_TYPES, Payment
from datetime import datetime

bp = Blueprint('main', __name__, url_prefix='/')

@bp.route('/', methods=['GET', 'HEAD'])
def index():
    try:
        current_app.logger.info('ルートパスへのアクセス')
        current_app.logger.info(f'認証状態: {current_user.is_authenticated}')
        current_app.logger.info(f'リクエストURL: {request.url}')
        current_app.logger.info(f'リクエストメソッド: {request.method}')
        current_app.logger.info(f'リクエストヘッダー: {dict(request.headers)}')
        
        if current_user.is_authenticated:
            current_app.logger.info('認証済みユーザー、予算ページへリダイレクト')
            return redirect(url_for('main.budgets'))
        current_app.logger.info('未認証ユーザー、ログインページへリダイレクト')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f'ルートパス処理エラー: {str(e)}')
        current_app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
        return render_template('error.html', error=str(e)), 500

@bp.route('/budgets')
@login_required
def budgets():
    try:
        current_app.logger.info('予算ページへのアクセス')
        current_app.logger.info(f'ユーザーID: {current_user.id}')
        properties = Property.query.filter_by(user_id=current_user.id).all()
        return render_template('budgets.html', properties=properties)
    except Exception as e:
        current_app.logger.error(f'予算ページ処理エラー: {str(e)}')
        current_app.logger.error(f'エラーの詳細: {e.__class__.__name__}')
        return render_template('error.html', error=str(e)), 500

@bp.route('/property/add', methods=['POST'])
@login_required
def add_property():
    code = request.form.get('code')
    name = request.form.get('name')
    contract_amount = request.form.get('contract_amount')
    budget_amount = request.form.get('budget_amount')

    if not all([code, name, contract_amount, budget_amount]):
        flash('すべての項目を入力してください')
        return redirect(url_for('main.budgets'))

    # 物件コードの重複チェック
    if Property.query.filter_by(code=code).first():
        flash('この物件コードは既に使用されています')
        return redirect(url_for('main.budgets'))

    try:
        property = Property(
            code=code,
            name=name,
            contract_amount=contract_amount,
            budget_amount=budget_amount,
            user_id=current_user.id
        )
        db.session.add(property)
        db.session.commit()
        flash('物件を登録しました')
    except Exception as e:
        db.session.rollback()
        flash('物件の登録に失敗しました')

    return redirect(url_for('main.budgets'))

@bp.route('/property/<int:id>')
@login_required
def property_detail(id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('この物件にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.budgets'))
    
    construction_budgets = ConstructionBudget.query.filter_by(property_id=id).all()
    now = datetime.now()
    return render_template('property_detail.html', 
                         property=property, 
                         construction_budgets=construction_budgets,
                         construction_types=CONSTRUCTION_TYPES,
                         now=now)

@bp.route('/property/<int:id>/edit', methods=['POST'])
@login_required
def edit_property(id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))

    property.code = request.form.get('code')
    property.name = request.form.get('name')
    property.contract_amount = request.form.get('contract_amount')
    property.budget_amount = request.form.get('budget_amount')

    try:
        db.session.commit()
        flash('物件情報を更新しました')
    except Exception as e:
        db.session.rollback()
        flash('物件情報の更新に失敗しました')

    return redirect(url_for('main.budgets'))

@bp.route('/property/<int:id>/delete', methods=['POST'])
@login_required
def delete_property(id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))

    try:
        db.session.delete(property)
        db.session.commit()
        flash('物件を削除しました')
    except Exception as e:
        db.session.rollback()
        flash('物件の削除に失敗しました')

    return redirect(url_for('main.budgets'))

@bp.route('/property/<int:id>/construction_budget', methods=['POST'])
@login_required
def add_construction_budget(id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('この物件にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.budgets'))
    
    code = request.form.get('code')
    name = request.form.get('name')
    amount = request.form.get('amount')
    
    if not all([code, name, amount]):
        flash('すべての項目を入力してください。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    try:
        amount = int(amount)
    except ValueError:
        flash('予算額は数値で入力してください。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    construction_budget = ConstructionBudget(
        code=code,
        name=name,
        amount=amount,
        property_id=id
    )
    
    try:
        db.session.add(construction_budget)
        db.session.commit()
        flash('工種予算を登録しました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('工種予算の登録に失敗しました。', 'error')
    
    return redirect(url_for('main.property_detail', id=id))

@bp.route('/property/<int:id>/construction_budget/<int:budget_id>', methods=['POST'])
@login_required
def update_construction_budget(id, budget_id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('この物件にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.budgets'))
    
    construction_budget = ConstructionBudget.query.get_or_404(budget_id)
    if construction_budget.property_id != id:
        flash('この工種予算にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    code = request.form.get('code')
    name = request.form.get('name')
    amount = request.form.get('amount')
    remaining_amount = request.form.get('remaining_amount')
    
    if not all([code, name, amount, remaining_amount]):
        flash('すべての項目を入力してください。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    try:
        amount = int(amount)
        remaining_amount = int(remaining_amount)
    except ValueError:
        flash('予算額と予算残額は数値で入力してください。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    construction_budget.code = code
    construction_budget.name = name
    construction_budget.amount = amount
    construction_budget.remaining_amount = remaining_amount
    
    try:
        db.session.commit()
        flash('工種予算を更新しました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('工種予算の更新に失敗しました。', 'error')
    
    return redirect(url_for('main.property_detail', id=id))

@bp.route('/property/<int:id>/construction_budget/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_construction_budget(id, budget_id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('この物件にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.budgets'))
    
    construction_budget = ConstructionBudget.query.get_or_404(budget_id)
    if construction_budget.property_id != id:
        flash('この工種予算にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    try:
        db.session.delete(construction_budget)
        db.session.commit()
        flash('工種予算を削除しました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('工種予算の削除に失敗しました。', 'error')
    
    return redirect(url_for('main.property_detail', id=id))

@bp.route('/property/<int:id>/construction_budget/<int:budget_id>/payment', methods=['POST'])
@login_required
def add_payment(id, budget_id):
    property = Property.query.get_or_404(id)
    if property.user_id != current_user.id:
        flash('この物件にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.budgets'))
    
    construction_budget = ConstructionBudget.query.get_or_404(budget_id)
    if construction_budget.property_id != id:
        flash('この工種予算にアクセスする権限がありません。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    payment_year = request.form.get('payment_year')
    payment_month = request.form.get('payment_month')
    vendor_name = request.form.get('vendor_name')
    payment_type = request.form.get('payment_type')
    payment_amount = request.form.get('payment_amount')
    remarks = request.form.get('remarks')
    
    if not all([payment_year, payment_month, vendor_name, payment_type, payment_amount]):
        flash('必須項目をすべて入力してください。', 'error')
        return redirect(url_for('main.property_detail', id=id))
    
    try:
        payment = Payment(
            year=int(payment_year),
            month=int(payment_month),
            vendor_name=vendor_name,
            payment_type=payment_type,
            amount=int(payment_amount),
            remarks=remarks,
            construction_budget_id=budget_id
        )
        db.session.add(payment)
        db.session.commit()
        flash('支払いを登録しました。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('支払いの登録に失敗しました。', 'error')
    
    return redirect(url_for('main.property_detail', id=id))

@bp.route('/property/<int:id>/budget/<int:budget_id>/payment/<int:payment_id>/edit', methods=['POST'])
@login_required
def edit_payment(id, budget_id, payment_id):
    property = Property.query.get_or_404(id)
    budget = ConstructionBudget.query.get_or_404(budget_id)
    payment = Payment.query.get_or_404(payment_id)

    # 支払いが該当の予算に属していることを確認
    if payment.construction_budget_id != budget_id or budget.property_id != id:
        abort(404)

    payment.year = request.form.get('payment_year', type=int)
    payment.month = request.form.get('payment_month', type=int)
    payment.vendor_name = request.form.get('vendor_name')
    payment.payment_type = request.form.get('payment_type')
    payment.amount = request.form.get('payment_amount', type=int)
    payment.remarks = request.form.get('remarks')

    db.session.commit()
    flash('支払い情報を更新しました')
    return redirect(url_for('main.property_detail', id=id))

@bp.route('/property/<int:id>/budget/<int:budget_id>/payment/<int:payment_id>/delete', methods=['POST'])
@login_required
def delete_payment(id, budget_id, payment_id):
    property = Property.query.get_or_404(id)
    budget = ConstructionBudget.query.get_or_404(budget_id)
    payment = Payment.query.get_or_404(payment_id)

    # 支払いが該当の予算に属していることを確認
    if payment.construction_budget_id != budget_id or budget.property_id != id:
        abort(404)

    db.session.delete(payment)
    db.session.commit()
    flash('支払い情報を削除しました')
    return redirect(url_for('main.property_detail', id=id)) 