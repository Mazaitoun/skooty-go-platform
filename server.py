# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file, render_template_string
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///skootygo.db")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False) # حقل الباسورد المشفر
    wallet_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TopupRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print("DB Connection Error (Ignored for stability):", e)

@app.route('/')
def home():
    return send_file('index.html')

# 1. إنشاء حساب جديد (Register)
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        phone = data.get('phone')
        full_name = data.get('name')
        password = data.get('password')

        if User.query.filter_by(phone=phone).first():
            return jsonify({"error": "رقم المحمول مسجل مسبقاً!"}), 400

        # تشفير الباسورد قبل حفظه
        hashed_password = generate_password_hash(password)
        new_user = User(phone=phone, full_name=full_name, password_hash=hashed_password, wallet_balance=0.0)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "تم إنشاء الحساب بنجاح", "user": {"id": new_user.id, "name": new_user.full_name, "balance": new_user.wallet_balance}})
    except Exception as e:
        return jsonify({"error": "حدث خطأ في السيرفر"}), 500

# 2. تسجيل الدخول (Login)
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        phone = data.get('phone')
        password = data.get('password')

        user = User.query.filter_by(phone=phone).first()
        
        # التأكد من المستخدم وصحة الباسورد
        if user and check_password_hash(user.password_hash, password):
            return jsonify({"message": "تم تسجيل الدخول", "user": {"id": user.id, "name": user.full_name, "balance": user.wallet_balance}})
        else:
            return jsonify({"error": "رقم المحمول أو كلمة المرور غير صحيحة!"}), 401
    except Exception as e:
        return jsonify({"error": "حدث خطأ أثناء تسجيل الدخول"}), 500

# 3. طلب شحن المحفظة
@app.route('/api/wallet/request_topup', methods=['POST'])
def request_topup():
    try:
        data = request.json
        req = TopupRequest(user_id=data.get('user_id', 1), amount=float(data['amount']), method=data['method'])
        db.session.add(req)
        db.session.commit()
        return jsonify({"message": "تم إرسال الطلب للمراجعة."})
    except:
        return jsonify({"message": "تم استلام الطلب."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
