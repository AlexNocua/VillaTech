"""Server-side Gmail OAuth with session-bound state and encrypted storage."""
import base64
import hashlib
import json
import secrets
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from .models import GmailAuthorization
from .views import staff_only

TOKEN_URL = 'https://oauth2.googleapis.com/token'
STATE_KEY = 'gmail_web_oauth'
SCOPE = 'https://www.googleapis.com/auth/gmail.send'


def cipher():
    from cryptography.fernet import Fernet
    return Fernet(settings.GMAIL_TOKEN_ENCRYPTION_KEY.encode('ascii'))


def callback_url():
    site = urlsplit(settings.PUBLIC_SITE_URL)
    if site.scheme != 'https' or not site.hostname or site.username or site.password:
        raise ValueError('HTTPS required')
    return f'{site.scheme}://{site.netloc}' + reverse('management:gmail_callback')


def ready():
    if not all((settings.GMAIL_WEB_CLIENT_ID, settings.GMAIL_WEB_CLIENT_SECRET,
                settings.GMAIL_TOKEN_ENCRYPTION_KEY, settings.GMAIL_WEB_ACCOUNT)):
        return False
    try:
        cipher()
        callback_url()
    except (ValueError, UnicodeError):
        return False
    return True


def credentials():
    if ready():
        row = GmailAuthorization.objects.filter(pk=1, client_id=settings.GMAIL_WEB_CLIENT_ID).first()
        if row:
            return (settings.GMAIL_WEB_CLIENT_ID, settings.GMAIL_WEB_CLIENT_SECRET,
                    cipher().decrypt(row.encrypted_token.encode('ascii')).decode('utf-8'))
    return settings.GMAIL_CLIENT_ID, settings.GMAIL_CLIENT_SECRET, settings.GMAIL_REFRESH_TOKEN


def _admin(request):
    if not request.user.is_superuser:
        raise PermissionDenied


@staff_only
@require_GET
def gmail_settings(request):
    _admin(request)
    return render(request, 'management/gmail_oauth.html', {
        'configured': ready(), 'authorization': GmailAuthorization.objects.filter(pk=1).first(),
        'gmail_account': settings.GMAIL_WEB_ACCOUNT,
    })


@staff_only
@require_POST
def gmail_start(request):
    _admin(request)
    if not ready():
        messages.error(request, 'Completa primero la configuración privada en Railway.')
        return redirect('management:gmail_settings')
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    request.session[STATE_KEY] = {'state': state, 'verifier': verifier, 'at': time.time(), 'user': request.user.pk}
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return redirect('https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': settings.GMAIL_WEB_CLIENT_ID, 'redirect_uri': callback_url(),
        'response_type': 'code', 'scope': SCOPE + ' openid email',
        'access_type': 'offline', 'prompt': 'consent', 'state': state,
        'code_challenge': challenge, 'code_challenge_method': 'S256',
        'login_hint': settings.GMAIL_WEB_ACCOUNT,
    }))


def google_json(req):
    with urlopen(req, timeout=settings.EMAIL_TIMEOUT) as response:
        return json.load(response)


@never_cache
@require_GET
def gmail_callback(request):
    # Do not redirect a callback containing an authorization code to login.
    if not request.user.is_active or not request.user.is_staff or not request.user.is_superuser:
        raise PermissionDenied
    saved = request.session.pop(STATE_KEY, None)
    state = request.GET.get('state', '')
    if (not ready() or not saved or saved['user'] != request.user.pk or
            not secrets.compare_digest(saved['state'], state) or
            not 0 <= time.time() - saved['at'] <= 600 or not request.GET.get('code') or request.GET.get('error')):
        messages.error(request, 'Autorización cancelada o vencida. Inicia nuevamente desde Gestión.')
        return redirect('management:gmail_settings')
    try:
        token = google_json(Request(TOKEN_URL, data=urlencode({
            'client_id': settings.GMAIL_WEB_CLIENT_ID, 'client_secret': settings.GMAIL_WEB_CLIENT_SECRET,
            'code': request.GET['code'], 'grant_type': 'authorization_code',
            'redirect_uri': callback_url(), 'code_verifier': saved['verifier'],
        }).encode()))
        if not token.get('refresh_token') or SCOPE not in token.get('scope', '').split():
            raise ValueError
        account = google_json(Request('https://openidconnect.googleapis.com/v1/userinfo',
            headers={'Authorization': 'Bearer ' + token['access_token']}))
        if account.get('email_verified') is not True or account.get('email', '').lower() != settings.GMAIL_WEB_ACCOUNT:
            raise ValueError
        encrypted = cipher().encrypt(token['refresh_token'].encode()).decode('ascii')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        messages.error(request, 'Google no autorizó el correo configurado. Verifica la cuenta y el permiso de envío.')
        return redirect('management:gmail_settings')
    GmailAuthorization.objects.update_or_create(pk=1, defaults={
        'encrypted_token': encrypted, 'client_id': settings.GMAIL_WEB_CLIENT_ID,
    })
    messages.success(request, 'Gmail autorizado. Puedes volver a la app; el próximo envío usará la nueva autorización.')
    return redirect('management:gmail_settings')
