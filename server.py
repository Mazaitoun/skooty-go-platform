# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import os
import time
from datetime import datetime

app = Flask(__name__)
CORS(app)

# قواعد البيانات المؤقتة المحفوظة للسيرفر
users = {
    "1": {
        "id": 1,
        "phone": "01234567890",
        "full_name": "محمود زيتون",
        "email": "user@skootygo.com",
        "national_id": "29901010000000",
        "wallet_balance": 150.0,
        "is_verified": True
    }
}

scooters = {
    1: {"id": 1, "code": "SKOTY-001", "model": "SKOOTY GO Pro", "battery": 88, "status": "available", "unlock_fee": 5.0, "minute_rate": 2.5},
    2: {"id": 2, "code": "SKOTY-002", "model": "SKOOTY GO Max", "battery": 75, "status": "available", "unlock_fee": 5.0, "minute_rate": 2.5}
}

active_rides = {}

@app.route('/')
def home():
    return send_file('index.html')

# --- 1️⃣ التسجيل وإدارة الملف الشخصي ---
@app.route('/api/auth/otp/verify', methods=['POST'])
def verify_otp():
    data = request.json or {}
    phone = data.get('phone', '01234567890')
    
    # استرجاع أو إنشاء بيانات الحساب
    user = users.get("1")
    user['phone'] = phone
    if data.get('full_name'): user['full_name'] = data.get('full_name')
    if data.get('national_id'): user['national_id'] = data.get('national_id')
    if data.get('email'): user['email'] = data.get('email')

    return jsonify({"token": "skooty_token_1", "user": user})

@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    return jsonify({"user": users["1"]})

# --- 2️⃣ شحن المحفظة (Wallet Recharge) ---
@app.route('/api/wallet/recharge', methods=['POST'])
def recharge_wallet():
    data = request.json or {}
    amount = float(data.get('amount', 0))
    if amount <= 0:
        return jsonify({"error": "مبلغ الشحن غير صحيح"}), 400
        
    users["1"]["wallet_balance"] += amount
    return jsonify({
        "message": f"تم شحن المحفظة بـ {amount} ج.م بنجاح",
        "new_balance": users["1"]["wallet_balance"]
    })

# --- 3️⃣ بدء الرحلة وحساب فتح القفل ---
@app.route('/api/scooters/unlock-by-qr', methods=['POST'])
def unlock_by_qr():
    user = users["1"]
    if user["wallet_balance"] < 10.0:
        return jsonify({"error": "رصيد المحفظة غير كافٍ لبدء الرحلة (الحد الأدنى 10 ج.م)"}), 400
        
    data = request.json or {}
    qr_code = data.get('qr_code', 'SKOTY-001')
    scooter_code = qr_code.split('/')[-1] if '/' in qr_code else qr_code
    
    scooter = next((s for s in scooters.values() if s['code'] == scooter_code), None)
    if not scooter:
        return jsonify({"error": "كود الإسكوتر غير صحيح"}), 404

    # تسجيل بدء الرحلة برسم فتح 5 ج.م + دقيقة بـ 2.5 ج.م
    ride_id = int(time.time())
    active_rides[ride_id] = {
        "ride_id": ride_id,
        "scooter_id": scooter["id"],
        "scooter_code": scooter["code"],
        "start_time": time.time(),
        "unlock_fee": scooter["unlock_fee"],
        "minute_rate": scooter["minute_rate"]
    }
    scooter["status"] = "rented"

    return jsonify({
        "ride_id": ride_id,
        "scooter_code": scooter["code"],
        "unlock_fee": scooter["unlock_fee"],
        "minute_rate": scooter["minute_rate"],
        "message": "تم فتح الإسكوتر لبدء الرحلة"
    })

# --- 4️⃣ إغلاق الرحلة وخصم التكلفة وإرجاع الباقي ---
@app.route('/api/scooters/lock-ride', methods=['POST'])
def lock_ride():
    data = request.json or {}
    ride_id = data.get('ride_id')
    
    # في حالة وجود رحلة نشطة أو حسابها افتراضياً
    ride = active_rides.get(ride_id)
    if not ride and active_rides:
        ride_id, ride = list(active_rides.items())[0]

    if ride:
        end_time = time.time()
        duration_seconds = max(10, int(end_time - ride["start_time"]))
        duration_minutes = max(1, int(duration_seconds / 60))
        
        # حساب التكلفة الكلية (رسوم الفتح + عدد الدقائق * سعر الدقيقة)
        total_fare = ride["unlock_fee"] + (duration_minutes * ride["minute_rate"])
        
        # الخصم من رصيد المحفظة
        user = users["1"]
        user["wallet_balance"] = max(0.0, user["wallet_balance"] - total_fare)
        
        # إرجاع حالة الإسكوتر لمتاح
        scooter = scooters.get(ride["scooter_id"])
        if scooter: scooter["status"] = "available"
        
        del active_rides[ride_id]

        return jsonify({
            "message": "تم إنهاء الرحلة بنجاح",
            "duration_minutes": duration_minutes,
            "total_fare": total_fare,
            "remaining_balance": user["wallet_balance"]
        })

    return jsonify({"error": "لا توجد رحلة نشطة حالياً"}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
