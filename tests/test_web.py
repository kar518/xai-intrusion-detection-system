"""The mounted lab must resolve its own assets and API under the shared host."""
import unittest

from src.web import app


class CombinedWebsiteTests(unittest.TestCase):
    def test_navigation_and_mounted_lab(self):
        client = app.test_client()
        dashboard = client.get('/')
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b'href="/lab/"', dashboard.data)
        lab = client.get('/lab', follow_redirects=True)
        self.assertEqual(lab.status_code, 200)
        self.assertIn(b'data-lab-base="/lab/"', lab.data)
        self.assertIn(b'href="/"', lab.data)
        self.assertIn(b'/lab/static/lab.js', lab.data)
        self.assertIn(b'/lab/static/lab.css', lab.data)
        self.assertEqual(client.get('/lab/static/lab.js').status_code, 200)
        self.assertEqual(client.get('/lab/static/lab.css').status_code, 200)
        case = client.get('/lab/api/case')
        self.assertEqual(case.status_code, 200)
        self.assertEqual(len(case.json['flow']), 65)
        reveal = client.post('/lab/api/reveal', json={'id': case.json['id']})
        self.assertEqual(reveal.status_code, 200)
        self.assertIn(reveal.json['label'], ('BENIGN', 'DDoS', 'PortScan', 'Bot'))
        self.assertEqual(client.get('/api/case').status_code, 404)
