import os
import json
import time
from functools import wraps
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-default-key')

# Simple dictionary for testing login
USERS = {
    'admin': 'jonathon'
}

# --- MQTT Configuration ---
MQTT_BROKER = os.environ.get('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_USERNAME = os.environ.get('MQTT_USERNAME')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD')

# Global state for latest telemetry
latest_telemetry = {
    "status": "offline",
    "ping_latency_ms": None,
    "temp_c": None
}

ping_start_time = None

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("capital_cooling/telemetry")
    client.subscribe("capital_cooling/ack")

def on_message(client, userdata, msg):
    global latest_telemetry, ping_start_time
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    print(f"Received MQTT message on {topic}: {payload}")

    try:
        data = json.loads(payload)
        if topic == "capital_cooling/telemetry":
            latest_telemetry.update(data)
            latest_telemetry["status"] = "online"
            latest_telemetry["last_seen"] = time.time()
        elif topic == "capital_cooling/ack":
            if data.get("status") == "ack" and ping_start_time is not None:
                latency = int((time.time() - ping_start_time) * 1000)
                latest_telemetry["ping_latency_ms"] = latency
                ping_start_time = None
    except Exception as e:
        print(f"Error parsing MQTT message: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1) if hasattr(mqtt, 'CallbackAPIVersion') else mqtt.Client()
if MQTT_USERNAME and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")

# --- Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cooling/<path:subpath>')
def cooling(subpath):
    return "Cooling System Details", 200

@app.route('/controls/<path:subpath>')
def controls(subpath):
    return "Control System Details", 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USERS and USERS[username] == password:
            session['user'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    flash('Successfully logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/telemetry', methods=['GET'])
@login_required
def get_telemetry():
    if latest_telemetry.get("last_seen"):
        if time.time() - latest_telemetry["last_seen"] > 15:
            latest_telemetry["status"] = "offline"
    return jsonify(latest_telemetry)

@app.route('/api/command/ping', methods=['POST'])
@login_required
def cmd_ping():
    global ping_start_time
    ping_start_time = time.time()
    mqtt_client.publish("capital_cooling/command", json.dumps({"action": "ping"}))
    return jsonify({"status": "sent", "message": "Ping command sent"})

@app.route('/api/command/read_sensors', methods=['POST'])
@login_required
def cmd_read_sensors():
    mqtt_client.publish("capital_cooling/command", json.dumps({"action": "read_sensors"}))
    return jsonify({"status": "sent", "message": "Read sensors command sent"})

@app.route('/api/command/pwm', methods=['POST'])
@login_required
def cmd_pwm():
    data = request.json
    value = data.get("value", 0)
    mqtt_client.publish("capital_cooling/command", json.dumps({"action": "pwm_set", "value": int(value)}))
    return jsonify({"status": "sent", "message": f"PWM set to {value}"})

@app.route('/api/alerts/inbound', methods=['POST'])
def api_alerts_inbound():
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(debug=True)
