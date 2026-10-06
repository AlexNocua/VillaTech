from unittest.mock import patch
from django.test import TestCase, override_settings

@override_settings(ALLOWED_HOSTS=['healthcheck.railway.app'], SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r'^healthz/$'])
class RailwayHealthTests(TestCase):
    def test_internal_probe_works_without_https(self):
        response=self.client.get('/healthz/', HTTP_HOST='healthcheck.railway.app')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{'status':'ok'})
    def test_database_failure_is_not_healthy(self):
        with patch('config.health.connection.cursor',side_effect=RuntimeError('offline')):
            response=self.client.get('/healthz/',HTTP_HOST='healthcheck.railway.app')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('offline',response.content.decode())
