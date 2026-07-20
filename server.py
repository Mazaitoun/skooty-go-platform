# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import json
import time
import random
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# المجلدات الآمنة لحفظ الصور المرفوعة من المستخدمين
UPLOAD_FOLDER = 'ride_photos'
ID_FOLDER = 'national_ids'

for folder in [UPLOAD_FOLDER, ID_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# قاعدة بيانات تجريبية مؤقتة لمنصة SKOOTY GO
users = {}
scooters = {
    1: {"id": 1, "code": "SKOTY-001", "model": "Xiaomi Pro 2", "battery": 88, "lat": 31.2001, "lng": 29.9187, "status": "available", "base_price": 5.0, "minute_price": 2.0},
    2: {"id": 2, "code": "SKOTY-002", "model": "Segway Ninebot", "battery": 75, "lat": 31.2050, "lng": 29.9200, "status": "available", "base_price": 5.0, "minute_price": 2.0},
    3: {"id": 3, "code": "SKOTY-003", "model": "Xiaomi Pro 2", "battery": 92, "lat": 31.1950, "lng": 29.9100, "status": "available", "base_price": 5.0, "minute_price": 2.0},
    4: {"id": 4, "code": "SKOTY-004", "model": "Segway Ninebot", "battery": 42, "lat": 31.2100, "lng": 29.9300, "status": "available", "base_price": 5.0, "minute_price": 2.0},
    5: {"id": 5, "code": "SKOTY-005", "model": "Xiaomi Pro 2", "battery": 65, "lat": 31.1850, "lng": 29.9000, "status": "available", "base_price": 5.0, "minute_price": 2.0},
}
rides = {}
user_id_counter = 1
ride_id_counter = 1

def send_mqtt_command(scooter_code, command):
    """
    محاكاة إرسال حزمة بيانات عبر بروتوكول MQTT إلى الـ Broker الخاص بـ SKOOTY GO
    Broker: mqtt.scooty.app | Topic: skootygo/hardware/{scooter_code}
    """
    print(f"📡 [MQTT - SKOOTY GO] Sending command [{command}] to scooter [{scooter_code}]")
    return True

@app.route('/')
def home():
    return send_file('index.html')

@app.route('/api/auth/otp/send', methods=['POST'])
def send_otp():
    data = request.json or {}
    phone = data.get('phone', '')
    print(f"📱 SKOOTY GO OTP generated for {phone}: 123456")
    return jsonify({"message": "OTP sent successfully", "expires_in": 300, "demo_otp": "123456"})

@app.route('/api/auth/otp/verify', methods=['POST'])
def verify_otp():
    global user_id_counter
    
    # استقبال البيانات كـ Form Data لدعم رفع ملف صورة البطاقة
    phone = request.form.get('phone', '')
    otp = request.form.get('otp', '')
    
    if otp != '123456':
        return jsonify({"error": "كود التحقق غير صحيح"}), 400
    
    user = None
    for u in users.values():
        if u['phone'] == phone:
            user = u
            break
            
    is_new = False
    if not user:
        email = request.form.get('email', '')
        full_name = request.form.get('full_name', '')
        national_id = request.form.get('national_id', '')
        address = request.form.get('address', '')
        id_image = request.files.get('id_image')

        # التحقق من شروط الأمن والسلامة للبيانات المطلوبة
        if not full_name:
            return jsonify({"error": "يجب إدخال الاسم بالكامل"}), 400
        if not national_id or len(national_id) != 14 or not national_id.isdigit():
            return jsonify({"error": "يجب إدخال رقم قومي صحيح مكون من 14 رقماً"}), 400
        if not id_image:
            return jsonify({"error": "يجب رفع أو تصوير بطاقة الرقم القومي لتفعيل الحساب"}), 400

        # حفظ صورة بطاقة الرقم القومي
        id_filename = f"id_{national_id}_{int(time.time())}.jpg"
        id_path = os.path.join(ID_FOLDER, id_filename)
        id_image.save(id_path)
        print(f"🪪 [SKOOTY GO] New User Registered! ID Photo saved at: {id_path}")

        user = {
            "id": user_id_counter,
            "phone": phone,
            "full_name": full_name,
            "email": email,
            "national_id": national_id,
            "address": address,
            "id_image_path": id_path,
            "wallet_balance": 150.0,
            "status": "active",
            "created_at": datetime.now().isoformat()
        }
        users[user_id_counter] = user
        user_id_counter += 1
        is_new = True
        
    token = f"skooty_go_token_{user['id']}_{int(time.time())}"
    return jsonify({"token": token, "user": user, "is_new_user": is_new})

@app.route('/api/scooters', methods=['GET'])
def get_scooters():
    lat = float(request.args.get('lat', 31.2001))
    lng = float(request.args.get('lng', 29.9187))
    
    available = [s.copy() for s in scooters.values() if s['status'] == 'available' and s['battery'] > 15]
    for s in available:
        s['distance'] = round(((s['lat'] - lat)**2 + (s['lng'] - lng)**2)**0.5 * 111000, 1)
    available.sort(key=lambda x: x['distance'])
    return jsonify({"scooters": available, "total": len(available)})

@app.route('/api/scooters/<int:scooter_id>/unlock', methods=['POST'])
def unlock_scooter(scooter_id):
    global ride_id_counter
    scooter = scooters.get(scooter_id)
    if not scooter or scooter['status'] != 'available':
        return jsonify({"error": "Scooter is not available for rental"}), 400
        
    send_mqtt_command(scooter['code'], "UNLOCK_VEHICLE")
    
    ride = {
        "id": ride_id_counter,
        "user_id": 1,
        "scooter_id": scooter_id,
        "scooter_code": scooter['code'],
        "status": "active",
        "start_latitude": scooter['lat'],
        "start_longitude": scooter['lng'],
        "start_time": datetime.now().isoformat(),
        "base_price": scooter['base_price'],
        "minute_price": scooter['minute_price'],
        "duration_minutes": 0,
        "total_fare": 0.0
    }
    rides[ride_id_counter] = ride
    ride_id_counter += 1
    scooter['status'] = 'rented'
    
    return jsonify({"ride": ride, "message": "Vehicle unlocked successfully!"})

@app.route('/api/scooters/<int:scooter_id>/lock', methods=['POST'])
def lock_scooter(scooter_id):
    data = request.form
    scooter = scooters.get(scooter_id)
    if not scooter:
        return jsonify({"error": "Vehicle not found"}), 404
        
    active_ride = None
    for r in rides.values():
        if r['scooter_id'] == scooter_id and r['status'] == 'active':
            active_ride = r
            break
            
    if not active_ride:
        return jsonify({"error": "No active ride found for this vehicle"}), 400

    # استقبال والتحقق من صورة إنهاء الرحلة الإلزامية
    image_file = request.files.get('photo')
    if not image_file:
        return jsonify({"error": "يجب تصوير الإسكوتر بوضوح للتأكد من قفله وسلامته قبل إنهاء الرحلة"}), 400

    # حفظ الصورة في المجلد المخصص
    photo_filename = f"ride_{active_ride['id']}_{int(time.time())}.jpg"
    photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
    image_file.save(photo_path)
    print(f"📸 [SKOOTY GO] End-Ride photo verified and saved at: {photo_path}")

    send_mqtt_command(scooter['code'], "LOCK_VEHICLE")
    
    start = datetime.fromisoformat(active_ride['start_time'])
    duration_seconds = (datetime.now() - start).total_seconds()
    duration_minutes = max(1, int(duration_seconds / 60))
    
    fare = active_ride['base_price'] + (duration_minutes * active_ride['minute_price'])
    
    active_ride['status'] = 'completed'
    active_ride['end_latitude'] = data.get('latitude', scooter['lat'])
    active_ride['end_longitude'] = data.get('longitude', scooter['lng'])
    active_ride['end_time'] = datetime.now().isoformat()
    active_ride['duration_minutes'] = duration_minutes
    active_ride['total_fare'] = fare
    active_ride['verification_photo'] = photo_path
    
    scooter['status'] = 'available'
    scooter['battery'] = max(10, scooter['battery'] - random.randint(2, 7))
    
    return jsonify({
        "ride": active_ride,
        "fare": {"duration": duration_minutes, "total": fare},
        "message": "Ride completed and vehicle locked safely."
    })

if __name__ == '__main__':
    print("⚡ SKOOTY GO production server initialized successfully.")
    app.run(host='0.0.0.0', port=5000, debug=True)
