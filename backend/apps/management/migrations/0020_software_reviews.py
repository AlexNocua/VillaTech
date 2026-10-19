from django.db import migrations,models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('management','0019_entry_final_image_quoteitem_final_image_and_more')]
    operations=[
        migrations.AlterField(model_name='productreview',name='entry',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name='reviews',to='management.entry')),
        migrations.AddField(model_name='productreview',name='development',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name='reviews',to='management.developmentproject')),
        migrations.AddField(model_name='productreview',name='review_type',field=models.CharField(choices=[('product','Impresión 3D / producto'),('software','Software / desarrollo')],default='product',max_length=10,verbose_name='Tipo de experiencia')),
        migrations.AddField(model_name='productreview',name='public_summary',field=models.TextField(blank=True,max_length=1000,verbose_name='Descripción pública (opcional)')),
        migrations.AddConstraint(model_name='productreview',constraint=models.UniqueConstraint(fields=('development','subject_key'),name='unique_project_review_subject')),
        migrations.AddConstraint(model_name='productreview',constraint=models.CheckConstraint(condition=(models.Q(entry__isnull=False,development__isnull=True)|models.Q(entry__isnull=True,development__isnull=False)),name='review_has_one_origin')),
    ]
