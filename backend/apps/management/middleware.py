from hashlib import sha256
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse

class LoginRateLimitMiddleware:
    """Shared cache is required for multiple workers; do not trust forwarded IPs."""
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        guarded=request.path in ['/gestion/ingresar/','/admin/login/'] and request.method=='POST'
        if not guarded: return self.get_response(request)
        ip=request.META.get('REMOTE_ADDR','unknown')
        if settings.TRUST_PROXY_HEADERS:
            ip=request.META.get('HTTP_X_REAL_IP',ip)
        key='login:'+sha256(ip.encode()).hexdigest()
        attempts=cache.get(key,0)
        if attempts>=10:
            response=HttpResponse('Demasiados intentos. Espera 15 minutos.',status=429)
            response['Retry-After']='900';return response
        if not cache.add(key,1,900):
            try: cache.incr(key)
            except ValueError: cache.set(key,1,900)
        response=self.get_response(request)
        if response.status_code==302 and request.user.is_authenticated: cache.delete(key)
        return response
