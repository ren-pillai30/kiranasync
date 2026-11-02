import os
import unittest
from backend.app import main

class StaticRoutesTests(unittest.TestCase):
    def setUp(self):
        main.app.config["TESTING"] = True
        main.app.config["LOGIN_DISABLED"] = True
        self.client = main.app.test_client()

    def test_root_index_html_loads(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<div id="root">', res.data)

    def test_manifest_json_serves_valid_pwa_spec(self):
        res = self.client.get('/manifest.json')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'KiranaSync', res.data)
        self.assertIn(b'standalone', res.data)

    def test_service_worker_serves_with_header(self):
        res = self.client.get('/sw.js')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get('Service-Worker-Allowed'), '/')
        self.assertIn(b'kiranasync-cache', res.data)

    def test_favicon_serves(self):
        res = self.client.get('/favicon.svg')
        self.assertEqual(res.status_code, 200)

    def test_spa_client_side_routing_falls_back_to_index(self):
        res = self.client.get('/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'<div id="root">', res.data)

    def test_api_404_returns_structured_json(self):
        res = self.client.get('/api/non-existent-endpoint')
        self.assertEqual(res.status_code, 404)
        self.assertTrue(res.is_json)

if __name__ == '__main__':
    unittest.main()
