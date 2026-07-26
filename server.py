# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# إعداد قاعدة البيانات - Supabase
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
    wallet_balance = db.Column(db.Float, default=150.0)

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    scooter_code = db.Column(db.String(20))
    status = db.Column(db.String(20), default="active")
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_fare = db.Column(db.Float, default=0.0)

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print("DB Warning:", e)

@app.route('/')
def home():
    return send_file('index.html')

# Endpoints أساسية للتأكد من استقرار السيرفر
@app.route('/api/health')
def health_check():
    return jsonify({"status": "SKOOTY GO Backend is Running perfectly!"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
