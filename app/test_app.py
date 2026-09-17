import unittest
import os
import json
from app.main import app, db
from app.models import User

class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.create_all()
            user = User(username='testadmin')
            user.set_password('dummy_test_pass')
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_login_logout(self):
        rv = self.client.post('/login', data=dict(
            username='testadmin',
            password='dummy_test_pass'
        ), follow_redirects=True)
        self.assertIn(b'Dashboard', rv.data)

        rv = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b'Login', rv.data)

    def test_protected_dashboard(self):
        rv = self.client.get('/dashboard', follow_redirects=True)
        self.assertIn(b'Login', rv.data)

    def test_api_ping_requires_auth(self):
        rv = self.client.post('/api/command/ping')
        self.assertEqual(rv.status_code, 302)

    def test_public_pages(self):
        pages = [
            '/',
            '/cooling/split-systems',
            '/cooling/water-cooled',
            '/cooling/internal-recirculating',
            '/cooling/portable-window-clip',
            '/controls/knx-automation',
            '/controls/door-access',
            '/controls/telecom-upgrades'
        ]
        for page in pages:
            rv = self.client.get(page)
            self.assertEqual(rv.status_code, 200, f"Page {page} failed to load.")
            self.assertIn(b"Portal Login", rv.data, f"Page {page} missing Portal Login link.")

    def test_webhook_inbound_json(self):
        rv = self.client.post('/api/alerts/inbound', json={"message": "Test alert"})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data), {"status": "received"})

    def test_webhook_inbound_form(self):
        rv = self.client.post('/api/alerts/inbound', data={"Body": "Form alert", "From": "123"})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(json.loads(rv.data), {"status": "received"})

if __name__ == '__main__':
    unittest.main()
