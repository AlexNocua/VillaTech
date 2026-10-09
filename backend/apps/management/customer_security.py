"""Safe recovery for the public quotation form; CSRF remains enforced."""
from functools import wraps
from django.shortcuts import render
from django.views.csrf import csrf_failure as default_csrf_failure
from django.views.decorators.cache import never_cache


def customer_headers(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        response = view(*args, **kwargs)
        response['Referrer-Policy'] = 'no-referrer'
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response
    return wrapped


@never_cache
@customer_headers
def csrf_failure(request, reason=''):
    match = request.resolver_match
    if match and match.view_name == 'management:customer_quote':
        # Never retry a POST or approve from an error handler. A fresh GET
        # rebuilds the form and its cookie; customer must explicitly approve.
        return render(request, 'management/customer_quote.html', {
            'security_error': True,
            'retry_url': request.path,
        }, status=403)
    return default_csrf_failure(request, reason=reason)
