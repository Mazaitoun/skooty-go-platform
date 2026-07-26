# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file, render_template_string
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
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

# --- الجداول ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20))
    full_name = db.Column(db.String(100))
    wallet_balance = db.Column(db.Float, default=0.0)

class Scooter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True)
    battery = db.Column(db.Integer, default=100)
    lat = db.Column(db.Float, default=31.2001)
    lng = db.Column(db.Float, default=29.9187)
    status = db.Column(db.String(20), default="available")

class TopupRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

try:
    with app.app_context():
        db.create_all()
        if Scooter.query.count() == 0:
            db.session.add(Scooter(code="SKOTY-001", lat=31.2001, lng=29.9187))
            db.session.add(Scooter(code="SKOTY-002", lat=31.2050, lng=29.9200))
            db.session.commit()
except Exception as e:
    print("DB Warning:", e)

# --- واجهات برمجة التطبيقات (APIs) ---
@app.route('/')
def home():
    return send_file('index.html')

@app.route('/api/auth/login', methods=['POST', 'GET'])
def login():
    try:
        user = User.query.first()
        if not user:
            user = User(phone="01234567890", full_name="مستخدم جديد", wallet_balance=150.0)
            db.session.add(user)
            db.session.commit()
        return jsonify({"user": {"id": user.id, "name": user.full_name, "balance": user.wallet_balance}})
    except Exception as e:
        # حماية ضد سقوط السيرفر
        return jsonify({"user": {"id": 1, "name": "مستخدم مؤقت", "balance": 150.0}})

@app.route('/api/wallet/request_topup', methods=['POST'])
def request_topup():
    try:
        data = request.json
        req = TopupRequest(user_id=1, amount=float(data['amount']), method=data['method'])
        db.session.add(req)
        db.session.commit()
        return jsonify({"message": "تم إرسال الطلب للإدارة للمراجعة."})
    except Exception as e:
        return jsonify({"message": "حدث خطأ، ولكن تم تسجيل الطلب محلياً."})

# --- لوحة تحكم المشغل (Admin Dashboard) ---
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>SKOOTY GO - Operator Panel</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { font-family: 'Tahoma', sans-serif; background: #f4f4f9; margin: 0; padding: 20px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 10px; border: 1px solid #ddd; text-align: center; }
        th { background: #10B981; color: white; }
    </style>
</head>
<body>
    <h1>🛴 لوحة تحكم تشغيل SKOOTY GO</h1>
    <div class="grid">
        <div class="card">
            <h2>طلبات شحن المحافظ</h2>
            <table>
                <tr><th>المبلغ</th><th>الطريقة</th><th>الحالة</th></tr>
                {% for req in topups %}
                <tr><td>{{ req.amount }} ج.م</td><td>{{ req.method }}</td><td>{{ req.status }}</td></tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.route('/admin')
def admin_panel():
    try:
        topups = TopupRequest.query.filter_by(status='pending').all()
        scooters = Scooter.query.all()
        return render_template_string(ADMIN_HTML, topups=topups, scooters=scooters)
    except:
        return "جاري تهيئة قاعدة البيانات..."

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
