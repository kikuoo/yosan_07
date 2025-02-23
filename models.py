class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... 既存のカラム ...
    contract_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=True)  # 請負契約への参照 