from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ---------- DB INIT ----------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS temperature (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value REAL,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- API ENDPOINT ----------
@app.route("/api/temperature", methods=["POST"])
def receive_temperature():
    data = request.json
    temp = data.get("temperature")
    time = data.get("time")

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO temperature (value, time) VALUES (?, ?)", (temp, time))
    conn.commit()
    conn.close()

    return jsonify({"status": "success"}), 200

# ---------- FETCH DATA ----------
@app.route("/api/data")
def get_data():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT value, time FROM temperature ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()

    return jsonify(rows)

# ---------- WEB PAGE ----------
@app.route("/")
def index():
    return render_template("index.html")

