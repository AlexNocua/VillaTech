from decimal import Decimal, InvalidOperation
from django import template
register=template.Library()
@register.filter
def co_number(value):
    try:
        number=Decimal(str(value))
        if not number.is_finite():return '—'
        precision=0 if number==number.to_integral_value() else 2
        return format(number,f',.{precision}f').replace(',','_').replace('.',',').replace('_','.')
    except (InvalidOperation,TypeError,ValueError):return '—'
