from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Property, ConstructionBudget

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/budgets')
@login_required
def budgets():
    properties = Property.query.filter_by(user_id=current_user.id).all()
    return render_template('budgets.html', properties=properties)

@main.route('/property/add', methods=['POST'])
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

@main.route('/property/<int:property_id>')
@login_required
def property_detail(property_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))
    construction_budgets = ConstructionBudget.query.filter_by(property_id=property_id).all()
    return render_template('property_detail.html', property=property, construction_budgets=construction_budgets)

@main.route('/property/<int:property_id>/edit', methods=['POST'])
@login_required
def edit_property(property_id):
    property = Property.query.get_or_404(property_id)
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

@main.route('/property/<int:property_id>/delete', methods=['POST'])
@login_required
def delete_property(property_id):
    property = Property.query.get_or_404(property_id)
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

@main.route('/property/<int:property_id>/budget/add', methods=['POST'])
@login_required
def add_construction_budget(property_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))

    code = request.form.get('code')
    name = request.form.get('name')
    amount = request.form.get('amount')

    if not all([code, name, amount]):
        flash('すべての項目を入力してください')
        return redirect(url_for('main.property_detail', property_id=property_id))

    try:
        budget = ConstructionBudget(
            code=code,
            name=name,
            amount=amount,
            property_id=property_id
        )
        db.session.add(budget)
        db.session.commit()
        flash('工事予算を登録しました')
    except Exception as e:
        db.session.rollback()
        flash('工事予算の登録に失敗しました')

    return redirect(url_for('main.property_detail', property_id=property_id))

@main.route('/property/<int:property_id>/budget/<int:budget_id>/edit', methods=['POST'])
@login_required
def edit_construction_budget(property_id, budget_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))

    budget = ConstructionBudget.query.get_or_404(budget_id)
    if budget.property_id != property_id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.property_detail', property_id=property_id))

    budget.code = request.form.get('code')
    budget.name = request.form.get('name')
    budget.amount = request.form.get('amount')

    try:
        db.session.commit()
        flash('工事予算を更新しました')
    except Exception as e:
        db.session.rollback()
        flash('工事予算の更新に失敗しました')

    return redirect(url_for('main.property_detail', property_id=property_id))

@main.route('/property/<int:property_id>/budget/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_construction_budget(property_id, budget_id):
    property = Property.query.get_or_404(property_id)
    if property.user_id != current_user.id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.budgets'))

    budget = ConstructionBudget.query.get_or_404(budget_id)
    if budget.property_id != property_id:
        flash('アクセス権限がありません')
        return redirect(url_for('main.property_detail', property_id=property_id))

    try:
        db.session.delete(budget)
        db.session.commit()
        flash('工事予算を削除しました')
    except Exception as e:
        db.session.rollback()
        flash('工事予算の削除に失敗しました')

    return redirect(url_for('main.property_detail', property_id=property_id)) 