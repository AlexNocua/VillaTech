"""Resend HTTPS transport for Railway plans without outbound SMTP."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

class ResendEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        count = 0
        for mail in email_messages:
            try:
                if not settings.RESEND_API_KEY:
                    raise ValueError('Configura RESEND_API_KEY')
                payload = {'from': mail.from_email, 'to': mail.to, 'subject': mail.subject, 'text': mail.body}
                for content, mime in getattr(mail, 'alternatives', []):
                    if mime == 'text/html': payload['html'] = content
                if mail.reply_to: payload['reply_to'] = mail.reply_to
                headers = {'Authorization': 'Bearer ' + settings.RESEND_API_KEY,
                    'Content-Type': 'application/json', 'User-Agent': 'VillaTech/1.0'}
                if mail.extra_headers.get('Idempotency-Key'):
                    headers['Idempotency-Key'] = mail.extra_headers['Idempotency-Key']
                request = Request('https://api.resend.com/emails', data=json.dumps(payload).encode(), headers=headers, method='POST')
                try:
                    with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                        result = json.load(response)
                except HTTPError as error:
                    raise RuntimeError(f'Resend HTTP {error.code}') from None
                if not result.get('id'): raise RuntimeError('Resend no confirmó el mensaje')
                count += 1
            except Exception:
                if not self.fail_silently: raise
        return count
