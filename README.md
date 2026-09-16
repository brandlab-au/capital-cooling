# Capital Cooling (Cloud-to-Hardware Control Platform)

This project provides a secure user authentication system and an interactive hardware command dashboard for the Arduino Uno R4 WiFi.

## Setup
1. Create a `.env` file based on `.env.example`.
2. Install dependencies: `pip install -r requirements.txt`.
3. Initialize the database and default user: `python manage.py init_db`.
4. Run the development server: `python app/main.py` or use gunicorn for production.

## Directories
- `app/`: Flask backend, templates, and static files.
- `arduino/`: Arduino C++ sketch and secrets.
- `deployment/`: Nginx, Systemd, and Mosquitto configuration files.
