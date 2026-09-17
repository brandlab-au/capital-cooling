import os
import json
import time
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from app.models import db, User

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test_key')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'capital_cooling.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- MQTT Configuration ---
MQTT_BROKER = os.environ.get('MQTT_BROKER', '127.0.0.1')
MQTT_PORT = int(os.environ.get('MQTT_PORT', 1883))
MQTT_USERNAME = os.environ.get('MQTT_USERNAME')
MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD')

# Global state for latest telemetry (in production, use a fast cache like Redis)
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
            # Ensure status is 'online' regardless of what telemetry payload says if it conflicts
            latest_telemetry["status"] = "online"
            # Update a last_seen timestamp here for timeout logic if desired
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

# We wrap MQTT connect in a try block so the app starts even if broker is down
try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")


# --- Routes ---
# --- Public Website Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cooling/split-systems')
def split_systems():
    return render_template('split_systems.html')

@app.route('/cooling/water-cooled')
def water_cooled():
    return render_template('water_cooled.html')

@app.route('/cooling/internal-recirculating')
def internal_recirculating():
    return render_template('internal_recirculating.html')

@app.route('/cooling/portable-window-clip')
def portable_window_clip():
    return render_template('portable_window_clip.html')

@app.route('/controls/door-access')
def door_access():
    return render_template('door_access.html')

@app.route('/controls/telecom-upgrades')
def telecom_upgrades():
    return render_template('telecom_upgrades.html')

@app.route('/api/alerts/inbound', methods=['POST'])
def webhook_inbound():
    data = None
    if request.is_json:
        data = request.json
    else:
        data = request.form.to_dict()

    print(f"Received inbound webhook payload: {data}")
    return jsonify({"status": "received"}), 200

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- API Endpoints ---
@app.route('/api/telemetry', methods=['GET'])
@login_required
def get_telemetry():
    # Timeout logic: offline if no telemetry for 15 seconds
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
