"""Gmail HTTPS API transport. OAuth secrets never appear in exception messages."""
import base64
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

class GmailAPIError(Exception):
    pass

class GmailAPIEmailBackend(BaseEmailBackend):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.access_token=None
    def open(self):
        if self.access_token:return False
        required=[settings.GMAIL_CLIENT_ID,settings.GMAIL_CLIENT_SECRET,settings.GMAIL_REFRESH_TOKEN]
        if not all(required):raise GmailAPIError('Faltan las credenciales OAuth de Gmail en el servidor.')
        data=urlencode({'client_id':required[0],'client_secret':required[1],'refresh_token':required[2],'grant_type':'refresh_token'}).encode()
        request=Request('https://oauth2.googleapis.com/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded'},method='POST')
        try:
            with urlopen(request,timeout=settings.EMAIL_TIMEOUT) as response:result=json.load(response)
        except HTTPError as error:
            raise GmailAPIError('Google rechazó la autorización OAuth (HTTP %s). Reautoriza la cuenta si el token expiró.' % error.code) from None
        except OSError:
            raise GmailAPIError('No se pudo conectar al servicio OAuth de Google por HTTPS.') from None
        except (ValueError,TypeError):
            raise GmailAPIError('Respuesta OAuth de Google no válida.') from None
        self.access_token=result.get('access_token')
        if not self.access_token:raise GmailAPIError('Google no devolvió un token de acceso.')
        return True
    def close(self):self.access_token=None
    def send_messages(self,email_messages):
        if not email_messages:return 0
        count=0
        for mail in email_messages:
            if not mail.recipients():continue
            try:
                self.open()
                # Django builds the full MIME message including HTML, Reply-To and attachments.
                raw=base64.urlsafe_b64encode(mail.message().as_bytes(linesep='\r\n')).decode('ascii')
                request=Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                    data=json.dumps({'raw':raw}).encode(),headers={'Authorization':'Bearer '+self.access_token,'Content-Type':'application/json'},method='POST')
                try:
                    with urlopen(request,timeout=settings.EMAIL_TIMEOUT) as response:result=json.load(response)
                except HTTPError as error:
                    raise GmailAPIError('Gmail rechazó el envío (HTTP %s). Revisa API habilitada, permisos y cuenta remitente.' % error.code) from None
                except OSError:
                    raise GmailAPIError('La conexión HTTPS con Gmail se interrumpió; el resultado del envío no se pudo confirmar.') from None
                except (ValueError,TypeError):
                    raise GmailAPIError('Gmail devolvió una respuesta de envío no válida.') from None
                if not result.get('id'):raise GmailAPIError('Gmail no confirmó el envío del mensaje.')
                count+=1
            except Exception:
                if not self.fail_silently:raise
        return count
