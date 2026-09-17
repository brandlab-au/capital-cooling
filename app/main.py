from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cooling/<path:subpath>')
def cooling(subpath):
    return "Cooling System Details", 200

@app.route('/controls/<path:subpath>')
def controls(subpath):
    return "Control System Details", 200

@app.route('/login')
def login():
    return "Login Page", 200

@app.route('/logout')
def logout():
    return "Logout Page", 200

@app.route('/api/alerts/inbound', methods=['POST'])
def api_alerts_inbound():
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(debug=True)
