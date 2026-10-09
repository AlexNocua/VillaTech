"""Safe recovery for the public quotation form; CSRF remains enforced."""
from functools import wraps
from django.shortcuts import render
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.cache import never_cache


def customer_headers(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        response = view(*args, **kwargs)
        # Django checks Referer on HTTPS when Origin is absent.
        # no-referrer breaks native forms; same-origin keeps the signed URL
        # private from other sites while allowing our CSRF-protected POST.
        response['Referrer-Policy'] = 'same-origin'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    return wrapped


@never_cache
@customer_headers
def csrf_failure(request, reason=''):
    match = request.resolver_match
    if match and match.view_name in ('management:customer_quote','management:customer_issue'):
        # Never retry a POST or approve from an error handler. A fresh GET
        # rebuilds the form and its cookie; customer must explicitly approve.
        return render(request, 'management/customer_quote.html', {
            'security_error': True,
            'retry_url': request.path,
            'support_url': __import__('django.urls',fromlist=['reverse']).reverse('management:customer_issue',args=[match.kwargs['token']]),
        }, status=403)
    return default_csrf_failure(request, reason=reason)
