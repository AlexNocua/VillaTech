from io import BytesIO
from .templatetags.management_numbers import co_number
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.utils import timezone
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class CircleLogo(Flowable):
    def __init__(self,path,size):
        super().__init__();self.path=path;self.width=self.height=size
    def draw(self):
        self.canv.saveState();path=self.canv.beginPath();path.circle(self.width/2,self.height/2,self.width*.47)
        self.canv.clipPath(path,stroke=0,fill=0)
        self.canv.drawImage(self.path,0,0,width=self.width,height=self.height,mask='auto')
        self.canv.restoreState()

def build_quote(order):
    output=BytesIO();styles=getSampleStyleSheet()
    fonts=Path(settings.BASE_DIR_TEMPLATES)/'static/landing/fonts'
    for name,file in [('VTSans','DejaVuSans.ttf'),('VTSerif','DejaVuSerif.ttf'),('VTBold','DejaVuSans-Bold.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
    styles['Heading2'].fontName='VTBold' 
    styles.add(ParagraphStyle(name='VTTitle',fontName='VTSerif',fontSize=27,leading=32,textColor=colors.HexColor('#07182A'),spaceAfter=14))
    styles.add(ParagraphStyle(name='VTTotal',fontName='VTBold',fontSize=20,leading=26,textColor=colors.HexColor('#07182A')))
    styles.add(ParagraphStyle(name='VTBody',fontName='VTSans',fontSize=10,leading=15,spaceAfter=8))
    styles.add(ParagraphStyle(name='VTMuted',fontName='VTSans',fontSize=8,leading=12,textColor=colors.HexColor('#525C57')))
    def text(value,style='VTBody'):return Paragraph(escape(str(value)).replace('\n','<br/>'),styles[style])
    def photo(field):
        if not field:return text('Sin imagen','VTMuted')
        with field.open('rb') as stream:
            raw=BytesIO(stream.read())
        width,height=ImageReader(raw).getSize();scale=min(7.6*cm/width,4.5*cm/height)
        return Image(raw,width*scale,height*scale)
    logo=Path(settings.BASE_DIR_TEMPLATES)/'static/landing/images'/('logo-dark-transparent.png' if order.logo_theme=='dark' else 'logo-light-transparent.png')
    header=Table([[CircleLogo(str(logo),2.8*cm),Paragraph('VillaTech<br/><font size=11>Donde tus ideas toman forma</font>',styles['VTTitle'])]],colWidths=[3.4*cm,13.4*cm])
    header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
    flow=[header,Spacer(1,16),text(f'COTIZACIÓN VT-{order.pk:06d}','VTTitle'),text(f'Cliente: {order.customer or "Por confirmar"}\nProyecto: {order.title}\nFecha: {timezone.localtime(order.created_at):%d/%m/%Y %H:%M} · Colombia')]
    if order.quote_expires_at:flow.append(text(f'Válida hasta: {timezone.localtime(order.quote_expires_at):%d/%m/%Y %H:%M} · Colombia','VTMuted'))
    if order.description:flow.append(text(order.description))
    items=list(order.items.all())
    for index,item in enumerate(items,1):
        detail=[text(f'{index:02d} · {item.name}','Heading2'),text(f'Medidas estimadas: {co_number(item.length_cm)} × {co_number(item.width_cm)} × {co_number(item.height_cm)} cm (largo × ancho × alto).\nCantidad: {item.quantity} · Unitario: $ {co_number(item.unit_price)} COP · Subtotal: $ {co_number(item.total)} COP')]
        if item.description:detail.append(text(item.description))
        primary=item.image or (item.variant.image if item.variant_id and item.variant.image else None)
        pictures=Table([[text('REFERENCIA DEL PRODUCTO','VTMuted'),text('COMPARACIÓN / ESCALA','VTMuted')],[photo(primary),photo(item.comparison_image)]],colWidths=[8.4*cm,8.4*cm])
        pictures.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F7F9F8')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#E4E9E6')),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
        detail.extend([pictures,Spacer(1,18)]);flow.append(KeepTogether(detail))
    if not items:
        flow.extend([text(f'Cantidad: {order.quantity} unidades · Unitario: $ {co_number(order.unit_price)} COP'),photo(order.image),Spacer(1,18)])
    total=sum((item.total for item in items),0) if items else order.amount
    summary=Table([[text('TOTAL ESTIMADO COP','VTBody'),text(f'$ {co_number(total)}','VTTotal')]],colWidths=[9*cm,7.8*cm]);summary.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#EAF8CC')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12)]))
    flow.extend([summary,Spacer(1,18),text('Cotización orientativa, sujeta a validación de geometría, material, color y acabado. No incluye envío ni impuestos adicionales salvo acuerdo expreso. No es factura ni comprobante de pago.','VTMuted')])
    def footer(canvas,doc):
        canvas.setStrokeColor(colors.HexColor('#159447'));canvas.line(42,46,553,46);canvas.setFont('VTSans',8);canvas.setFillColor(colors.HexColor('#525C57'));canvas.drawString(42,31,'VillaTech · Ubaté, Cundinamarca · villatechingenieria@gmail.com');canvas.drawRightString(553,31,f'Página {doc.page}')
    SimpleDocTemplate(output,pagesize=(595.28,841.89),leftMargin=42,rightMargin=42,topMargin=34,bottomMargin=65,title=f'Cotización VT-{order.pk}',author='VillaTech').build(flow,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()
