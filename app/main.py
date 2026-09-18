import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'super-secret-default-key')

# Simple dictionary for testing login
USERS = {
    'admin': 'jonathon'
}

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
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USERS and USERS[username] == password:
            session['user'] = username
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    return "Logout Page", 200

@app.route('/api/alerts/inbound', methods=['POST'])
def api_alerts_inbound():
    return jsonify({"status": "received"}), 200

if __name__ == '__main__':
    app.run(debug=True)
