# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file
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
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    full_name = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    wallet_balance = db.Column(db.Float, default=50.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TopupRequest(db.Model):
    __tablename__ = 'topup_request'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print("DB Error:", e)

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        phone = data.get('phone')
        full_name = data.get('name')
        password = data.get('password')

        if User.query.filter_by(phone=phone).first():
            return jsonify({"error": "رقم المحمول مسجل مسبقاً!"}), 400

        hashed_password = generate_password_hash(password)
        new_user = User(phone=phone, full_name=full_name, password_hash=hashed_password, wallet_balance=50.0)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "تم إنشاء الحساب بنجاح", 
            "user": {"id": new_user.id, "name": new_user.full_name, "balance": new_user.wallet_balance}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        phone = data.get('phone')
        password = data.get('password')

        user = User.query.filter_by(phone=phone).first()
        if user and check_password_hash(user.password_hash, password):
            return jsonify({
                "message": "تم تسجيل الدخول", 
                "user": {"id": user.id, "name": user.full_name, "balance": user.wallet_balance}
            })
        else:
            return jsonify({"error": "رقم المحمول أو كلمة المرور غير صحيحة!"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/balance/<int:user_id>', methods=['GET'])
def get_balance(user_id):
    user = User.query.get(user_id)
    if user:
        return jsonify({"balance": user.wallet_balance})
    return jsonify({"error": "المستخدم غير موجود"}), 404

@app.route('/api/wallet/request_topup', methods=['POST'])
def request_topup():
    try:
        data = request.json
        req = TopupRequest(
            user_id=int(data.get('user_id')),
            amount=float(data.get('amount')),
            method=data.get('method')
        )
        db.session.add(req)
        db.session.commit()
        return jsonify({"message": "تم إرسال طلب الشحن بنجاح!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin')
def admin_panel():
    try:
        # استعلام مباشر وآمن لجلب الطلبات مع المستخدمين
        pending_topups = db.session.query(TopupRequest, User).filter(
            TopupRequest.user_id == User.id,
            TopupRequest.status == 'pending'
        ).all()
        
        total_users = User.query.count()
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>لوحة تحكم SKOOTY GO الاحترافية</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
                * {{ font-family: 'Cairo', sans-serif; box-sizing: border-box; }}
                body {{ background: #0F172A; color: #F8FAFC; margin: 0; padding: 30px; }}
                .container {{ max-width: 1000px; margin: 0 auto; }}
                h1 {{ color: #10B981; text-align: center; margin-bottom: 30px; }}
                .stats {{ display: flex; gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: #1E293B; padding: 20px; border-radius: 12px; flex: 1; text-align: center; border: 1px solid #334155; }}
                .stat-card h3 {{ color: #94A3B8; margin: 0 0 10px 0; font-size: 16px; }}
                .stat-card p {{ color: #10B981; font-size: 28px; font-weight: bold; margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; background: #1E293B; border-radius: 12px; overflow: hidden; border: 1px solid #334155; }}
                th, td {{ padding: 15px; text-align: center; border-bottom: 1px solid #334155; }}
                th {{ background: #334155; color: #F8FAFC; }}
                tr:hover {{ background: #262F40; }}
                .btn-approve {{ background: #10B981; color: white; padding: 8px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; transition: 0.2s; }}
                .btn-approve:hover {{ background: #059669; }}
                .empty {{ text-align: center; padding: 40px; color: #94A3B8; font-size: 18px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>SKOOTY GO - لوحة الإدارة الرئيسية 🚀</h1>
                <div class="stats">
                    <div class="stat-card">
                        <h3>إجمالي المستخدمين</h3>
                        <p>{total_users}</p>
                    </div>
                    <div class="stat-card">
                        <h3>طلبات الشحن المعلقة</h3>
                        <p>{len(pending_topups)}</p>
                    </div>
                </div>
                <h2 style="margin-bottom: 15px;">طلبات الشحن بانتظار الموافقة</h2>
                <table>
                    <tr>
                        <th>رقم الطلب</th>
                        <th>اسم العميل</th>
                        <th>رقم التليفون</th>
                        <th>المبلغ</th>
                        <th>طريقة الدفع</th>
                        <th>الإجراء</th>
                    </tr>
        """
        
        if not pending_topups:
            html += "<tr><td colspan='6' class='empty'>لا توجد طلبات شحن معلقة حالياً ✅</td></tr>"
        else:
            for t, u in pending_topups:
                html += f"""
                    <tr>
                        <td>#{t.id}</td>
                        <td>{u.full_name}</td>
                        <td>{u.phone}</td>
                        <td style="color: #10B981; font-weight: bold;">{t.amount} ج.م</td>
                        <td>{t.method}</td>
                        <td><a href="/admin/approve?id={t.id}" class="btn-approve">موافقة وشحن الرصيد ⚡</a></td>
                    </tr>
                """
        
        html += """
                </table>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"خطأ في لوحة التحكم: {e}"

@app.route('/admin/approve')
def approve_topup():
    try:
        req_id = request.args.get('id')
        topup = TopupRequest.query.get(req_id)
        if topup and topup.status == 'pending':
            topup.status = 'approved'
            user = User.query.get(topup.user_id)
            if user:
                user.wallet_balance = float(user.wallet_balance) + float(topup.amount)
                db.session.commit()
            return """
            <body style="background:#0F172A; color:white; font-family:Tahoma; text-align:center; padding-top:50px;">
                <h2 style="color:#10B981;">تمت الموافقة بنجاح وإضافة الرصيد لحساب العميل! 🎉</h2>
                <br><a href="/admin" style="background:#10B981; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">العودة لوحة التحكم</a>
            </body>
            """
        return "<body style='background:#0F172A; color:white; text-align:center; padding-top:50px;'><h2>الطلب غير موجود أو تم معالجته مسبقاً.</h2><br><a href='/admin' style='color:#10B981;'>العودة</a></body>"
    except Exception as e:
        return f"خطأ: {e}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
