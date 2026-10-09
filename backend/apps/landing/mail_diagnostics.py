"""Safe transport diagnostics: never expose credentials or provider response bodies."""
import errno
import socket
import smtplib
import ssl

def mail_error_summary(error):
    from .gmail_backend import GmailAPIError
    if isinstance(error,GmailAPIError):return str(error)
    if isinstance(error,smtplib.SMTPAuthenticationError):
        return 'Gmail rechazó el acceso. Revisa la cuenta y la contraseña de aplicación.'
    if isinstance(error,smtplib.SMTPRecipientsRefused):
        return 'El servidor rechazó el destinatario. Revisa su dirección de correo.'
    if isinstance(error,smtplib.SMTPSenderRefused):
        return 'El servidor rechazó el remitente. Revisa DEFAULT_FROM_EMAIL.'
    if isinstance(error,ssl.SSLError):
        return 'Falló la conexión segura TLS con el servidor de correo.'
    if isinstance(error,socket.gaierror):
        return 'No se pudo resolver el servidor de correo (DNS).'
    if isinstance(error,(TimeoutError,socket.timeout)):
        return 'Se agotó el tiempo al conectar o enviar por SMTP.'
    if isinstance(error,OSError):
        code=getattr(error,'errno',None)
        if code in (errno.ENETUNREACH,errno.EHOSTUNREACH):
            return 'El servidor no puede alcanzar la red SMTP. Revisa la salida de red del alojamiento.'
        if code == errno.ECONNREFUSED:
            return 'La conexión SMTP fue rechazada. Revisa el host, puerto y acceso de red.'
        if code in (errno.ECONNRESET,errno.EPIPE):
            return 'La conexión SMTP se interrumpió. Puedes reintentar el correo.'
        return 'Error de conexión SMTP. Revisa los logs y ejecuta check_email_connection.'
    return type(error).__name__ + ': revisa la configuración y los logs del servidor.'

def safe_error_code(error):
    code=getattr(error,'errno',None)
    smtp_code=getattr(error,'smtp_code',None)
    return f'{type(error).__name__} errno={code if isinstance(code,int) else "n/a"} smtp={smtp_code if isinstance(smtp_code,int) else "n/a"}'
