"""Run locally only. Writes OAuth secrets to a private file, never prints them."""
import argparse
import json
import os
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description='Autoriza Gmail localmente, sin enviar mensajes.')
    parser.add_argument('--client',required=True,help='JSON de cliente OAuth tipo Escritorio descargado de Google')
    parser.add_argument('--output',default='gmail-railway.env')
    args=parser.parse_args()
    target=Path(args.output)
    if target.exists():parser.error('El archivo de salida ya existe. Usa otro nombre o retíralo antes de reautorizar.')
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow=InstalledAppFlow.from_client_secrets_file(args.client,['https://www.googleapis.com/auth/gmail.send'])
    credentials=flow.run_local_server(host='127.0.0.1',port=0,access_type='offline',prompt='consent',
        authorization_prompt_message='Abre el navegador y autoriza únicamente la cuenta remitente de VillaTech.',
        success_message='Autorización completada. Puedes cerrar esta pestaña.')
    if not credentials.refresh_token:raise RuntimeError('Google no entregó un token de actualización. Repite la autorización.')
    values={'EMAIL_PROVIDER':'gmail_api','EMAIL_BACKEND':'apps.landing.gmail_backend.GmailAPIEmailBackend',
        'GMAIL_CLIENT_ID':credentials.client_id,'GMAIL_CLIENT_SECRET':credentials.client_secret,'GMAIL_REFRESH_TOKEN':credentials.refresh_token}
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as file:
        file.write('\n'.join(key+'='+value for key,value in values.items())+'\n')
    print('Autorización guardada en '+str(target)+'. Copia las variables a Railway; no compartas este archivo.')

if __name__=='__main__':
    try:main()
    except Exception:
        raise SystemExit('No se completó la autorización. Revisa el cliente OAuth, usuario autorizado y conexión a Google; no compartas credenciales.') from None
