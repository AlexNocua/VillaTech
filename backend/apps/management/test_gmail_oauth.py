from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .gmail_oauth import SCOPE, credentials
from .models import GmailAuthorization


@override_settings(
    PUBLIC_SITE_URL='https://www.villatechubate.com',
    GMAIL_WEB_CLIENT_ID='web-client', GMAIL_WEB_CLIENT_SECRET='test-client-secret',
    GMAIL_WEB_ACCOUNT='studio@example.com', GMAIL_TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode(),
    GMAIL_CLIENT_ID='legacy', GMAIL_CLIENT_SECRET='legacy-secret', GMAIL_REFRESH_TOKEN='legacy-token',
)
class GmailOAuthTest(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('admin', password='test-pass')
        self.client.force_login(self.admin)

    def authorize(self, email):
        start = self.client.post(reverse('management:gmail_start'))
        params = parse_qs(urlsplit(start['Location']).query)
        self.assertEqual(params['code_challenge_method'], ['S256'])
        callback = reverse('management:gmail_callback')
        with patch('apps.management.gmail_oauth.google_json', side_effect=[
            {'access_token': 'access', 'refresh_token': 'fresh-token', 'scope': SCOPE},
            {'email': email, 'email_verified': True},
        ]) as google:
            self.client.get(callback, {'code': 'test-code', 'state': 'incorrect'})
            google.assert_not_called()
            start = self.client.post(reverse('management:gmail_start'))
            state = parse_qs(urlsplit(start['Location']).query)['state'][0]
            self.client.get(callback, {'code': 'test-code', 'state': state})
            self.client.get(callback, {'code': 'test-code', 'state': state})
            self.assertEqual(google.call_count, 2)

    def test_saves_encrypted_refresh_token_and_preserves_environment_fallback(self):
        self.assertEqual(credentials()[2], 'legacy-token')
        self.authorize('studio@example.com')
        self.assertNotIn('fresh-token', GmailAuthorization.objects.get().encrypted_token)
        self.assertEqual(credentials(), ('web-client', 'test-client-secret', 'fresh-token'))
        self.assertNotContains(self.client.get(reverse('management:gmail_settings')), 'fresh-token')

    def test_rejects_different_account(self):
        self.authorize('other@example.com')
        self.assertFalse(GmailAuthorization.objects.exists())
        self.assertEqual(credentials()[2], 'legacy-token')

    def test_staff_without_superuser_cannot_authorize(self):
        user = get_user_model().objects.create_user('staff', is_staff=True)
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse('management:gmail_start')).status_code, 403)


class PersistentGmailKeyTest(TestCase):
    @override_settings(GMAIL_TOKEN_ENCRYPTION_KEY='')
    def test_provisions_once_and_reads_existing_key(self):
        import os
        import tempfile
        from pathlib import Path
        from .gmail_oauth import cipher, key_path, provision_key
        with tempfile.TemporaryDirectory() as mount, patch.dict(os.environ, {'RAILWAY_VOLUME_MOUNT_PATH': mount}), override_settings(MEDIA_ROOT=Path(mount)/'media'):
            provision_key()
            token = cipher().encrypt(b'verification')
            key = key_path()
            original = key.read_bytes()
            provision_key()
            self.assertEqual(key.read_bytes(), original)
            self.assertEqual(cipher().decrypt(token), b'verification')
            self.assertEqual(key.stat().st_mode & 0o777, 0o600)
