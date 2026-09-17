import argparse
import os
from dotenv import load_dotenv
from flask import Flask
from app.models import db, User

load_dotenv()

app = Flask(__name__)
# Adjust path assuming database will be in the instance folder or similar
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'capital_cooling.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def init_db():
    with app.app_context():
        db.create_all()
        print("Database initialized.")

        # Check if admin exists
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', '')

        admin_user = User.query.filter_by(username=admin_username).first()
        if not admin_user:
            print(f"Creating default admin user: {admin_username}")
            admin_user = User(username=admin_username)
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created successfully.")
        else:
            print("Default admin user already exists.")

def create_user(username, password):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            print(f"User {username} already exists.")
            return

        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        print(f"User {username} created successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage Capital Cooling Platform")
    parser.add_argument('command', choices=['init_db', 'create_user'], help="Command to run")
    parser.add_argument('--username', help="Username for create_user")
    parser.add_argument('--password', help="Password for create_user")

    args = parser.parse_args()

    if args.command == 'init_db':
        init_db()
    elif args.command == 'create_user':
        if not args.username or not args.password:
            print("Please provide --username and --password")
        else:
            create_user(args.username, args.password)
