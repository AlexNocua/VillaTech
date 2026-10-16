"""Read-only operational calendar; dates follow the configured local timezone."""
import calendar
from urllib.parse import urlencode
from datetime import date, datetime, time, timedelta
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from .views import staff_only
from .models import Entry
from .commercial_filters import filter_payment, PAYMENT_CHOICES

MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']

@staff_only
@require_GET
def calendar_view(request):
    today=timezone.localdate()
    try:
        selected=date.fromisoformat(request.GET.get('date',''))
        if not 1901<=selected.year<=2098:raise ValueError
    except (ValueError,TypeError):selected=today
    mode=request.GET.get('view','month')
    if mode not in ('day','week','month'):mode='month'
    basis=request.GET.get('basis','created')
    if basis not in ('created','delivery'):basis='created'
    if mode=='month':
        weeks=calendar.Calendar(firstweekday=0).monthdatescalendar(selected.year,selected.month)
        start,end=weeks[0][0],weeks[-1][-1]+timedelta(days=1)
        previous=(selected.replace(day=1)-timedelta(days=1)).replace(day=1)
        following=(selected.replace(day=28)+timedelta(days=4)).replace(day=1)
        heading=f'{MONTHS[selected.month-1].capitalize()} {selected.year}'
    else:
        start=selected if mode=='day' else selected-timedelta(days=selected.weekday())
        end=start+timedelta(days=1 if mode=='day' else 7)
        weeks=[[start+timedelta(days=i) for i in range((end-start).days)]]
        previous,following=selected-(end-start),selected+(end-start)
        heading=f'{start:%d/%m/%Y}' if mode=='day' else f'{start:%d/%m} – {(end-timedelta(days=1)):%d/%m/%Y}'
    entries=Entry.objects.filter(kind__in=['order','sale']).prefetch_related('items')
    status=request.GET.get('status','');payment=request.GET.get('payment','');query=request.GET.get('q','').strip()[:150]
    if status in dict(Entry.STATUS):entries=entries.filter(status=status)
    entries=filter_payment(entries,payment)
    if query:entries=entries.filter(Q(title__icontains=query)|Q(customer__icontains=query)|Q(customer_email__icontains=query))
    undated=entries.filter(kind='order',status__in=['pending','printing','ready'],estimated_delivery_date__isnull=True).count()
    if basis=='delivery':visible=entries.filter(estimated_delivery_date__gte=start,estimated_delivery_date__lt=end).order_by('estimated_delivery_date','created_at')
    else:
        zone=timezone.get_current_timezone()
        visible=entries.filter(created_at__gte=timezone.make_aware(datetime.combine(start,time.min),zone),created_at__lt=timezone.make_aware(datetime.combine(end,time.min),zone)).order_by('created_at')
    grouped={};events=[]
    for entry in visible:
        day=entry.estimated_delivery_date if basis=='delivery' else timezone.localtime(entry.created_at).date()
        event={'time':timezone.localtime(entry.created_at).strftime('%H:%M') if basis=='created' else 'Sin hora','id':entry.pk,'title':entry.title,'customer':entry.customer or 'Cliente por definir','date':day.isoformat(),'status':entry.get_status_display(),'status_code':entry.status,'payment':entry.payment_label,'units':entry.total_units,'amount':str(entry.amount),'balance':str(entry.outstanding),'delivery':entry.estimated_delivery_date.isoformat() if entry.estimated_delivery_date else 'Sin programar','url':reverse('management:workflow_detail',args=[entry.pk])}
        grouped.setdefault(day,[]).append(event);events.append(event)
    def link(**changes):
        params=request.GET.copy();params['view']=mode;params['date']=selected.isoformat();params['basis']=basis
        for key,value in changes.items():params[key]=value
        return '?'+params.urlencode()
    rows=[]
    for week in weeks:
        rows.append([{'date':day,'today':day==today,'selected':day==selected,'outside':day.month!=selected.month,'events':grouped.get(day,[]),'url':link(date=day.isoformat())} for day in week])
    return render(request,'management/calendar.html',{'rows':rows,'events':events,'selected_events':grouped.get(selected,[]),'selected':selected,'mode':mode,'basis':basis,'heading':heading,'today':today,'previous_url':link(date=previous.isoformat()),'next_url':link(date=following.isoformat()),'today_url':link(date=today.isoformat()),'view_links':[{'key':key,'label':label,'url':link(view=key)} for key,label in [('day','Día'),('week','Semana'),('month','Mes')]],'status':status,'statuses':[(key,label) for key,label in Entry.STATUS if key in ('pending','printing','ready','delivered','sold','cancelled')],'payment':payment,'payment_choices':PAYMENT_CHOICES,'query':query,'undated':undated,'undated_url':reverse('management:workflow')+'?'+urlencode({'stage':'orders','due':'undated','q':query,'status':status,'payment':payment}),'total':len(events)})
