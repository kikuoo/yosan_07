from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    contract_amount = db.Column(db.Integer, nullable=False)
    budget_amount = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('properties', lazy=True))
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class ConstructionBudget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey('property.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    property = db.relationship('Property', backref=db.backref('budgets', lazy=True))
    payments = db.relationship('Payment', backref='budget', lazy=True, cascade='all, delete-orphan')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    vendor_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    is_contract = db.Column(db.Boolean, nullable=False, default=True)  # True: 請負, False: 請負外
    note = db.Column(db.Text)
    budget_id = db.Column(db.Integer, db.ForeignKey('construction_budget.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def payment_type(self):
        return '請負' if self.is_contract else '請負外'

# 工種コードと工種名のマッピング
CONSTRUCTION_TYPES = {
    '41-01': '準備費',
    '41-02': '仮設物費',
    '41-03': '廃棄物処分費',
    '41-04': '共通仮設',
    '41-05': '直接仮設工事',
    '41-90': '仮設工事一式',
    '42-01': '土工事',
    '42-02': '地業工事',
    '42-03': '鉄筋工事',
    '42-04': '型枠工事',
    '42-05': 'ｺﾝｸﾘｰﾄ工事',
    '42-06': '鉄骨工事',
    '42-07': '組積ALC工事',
    '42-08': '防水工事',
    '42-09': '石工事',
    '42-10': 'タイル工事',
    '42-11': '木工事',
    '42-12': '屋根工事',
    '42-13': '外装工事',
    '42-14': '金属工事',
    '42-15': '左官工事',
    '42-16': '木製建具工事',
    '42-17': '金属製建具工事',
    '42-18': '硝子工事',
    '42-19': '塗装吹付工事',
    '42-20': '内装工事',
    '42-21': '家具・雑工事',
    '42-22': '仮設事務所工事',
    '42-23': 'プール工事',
    '42-24': 'サイン工事',
    '42-25': '厨房機器工事',
    '42-26': '既存改修工事',
    '42-27': '特殊付帯工事',
    '42-28': '住宅設備工事',
    '42-29': '雑工事',
    '42-90': '建築工事一式',
    '43-01': '解体工事',
    '43-02': '外構開発工事',
    '43-03': '附帯建物工事',
    '43-04': '別途外構工事',
    '43-05': '山留工事',
    '43-06': '杭工事',
    '43-90': '解体外構附帯工事一式',
    '44-01': '電気設備工事',
    '44-02': '給排水衛生設備工事',
    '44-03': '空調換気設備工事',
    '44-04': '浄化槽工事',
    '44-05': '昇降機工事',
    '44-06': 'オイル配管設備工事',
    '44-07': '厨房機器工事',
    '44-08': 'ガス設備工事',
    '44-09': '消防設備工事',
    '44-90': '設備工事一式',
    '44-91': '諸経費',
    '45-01': '追加変更工事',
    '45-02': '追加変更工事２',
    '45-10': 'その他工事',
    '45-90': '追加変更一式',
    '46-01': '建築一式工事',
    '46-02': '許認可代顔料',
    '46-10': 'その他工事',
    '61-01': '管理給与',
    '61-02': '共通給与',
    '61-03': '舗装給与',
    '61-04': '建設業退職金共済掛金',
    '61-06': '油脂費',
    '61-10': '法定福利費（労災保険）',
    '61-15': '事務用品費',
    '61-16': '通信交通費',
    '61-18': '租税公課（印紙）',
    '61-20': '保険料（工事保険）',
    '61-22': '福利厚生費（被服・薬品）',
    '61-25': '設計費（施工図費）',
    '61-30': '雑費（打ち合わせ・式典）'
}