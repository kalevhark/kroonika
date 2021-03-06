# Generated by Django 2.1.2 on 2018-12-23 14:56

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wiki', '0003_delete_pilt'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pilt',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nimi', models.CharField(max_length=100, verbose_name='Pealkiri')),
                ('autor', models.CharField(blank=True, max_length=100, null=True, verbose_name='Autor')),
                ('kirjeldus', models.TextField(blank=True, null=True, verbose_name='Kirjeldus')),
                ('pilt', models.ImageField(blank=True, max_length=255, null=True, upload_to='pildid/%Y/%m/%d/')),
                ('hist_date', models.DateField(blank=True, null=True, verbose_name='Kuupäev')),
                ('hist_year', models.IntegerField(blank=True, help_text='Aasta', null=True, verbose_name='Aasta')),
                ('hist_month', models.PositiveSmallIntegerField(blank=True, choices=[(1, 'jaanuar'), (2, 'veebruar'), (3, 'märts'), (4, 'aprill'), (5, 'mai'), (6, 'juuni'), (7, 'juuli'), (8, 'august'), (9, 'september'), (10, 'oktoober'), (11, 'november'), (12, 'detsember')], help_text='ja/või kuu', null=True, verbose_name='Kuu')),
                ('profiilipilt_kroonika', models.BooleanField(default=False, verbose_name='Allika profiilipilt')),
                ('profiilipilt_artikkel', models.BooleanField(default=False, verbose_name='Artikli profiilipilt')),
                ('profiilipilt_isik', models.BooleanField(default=False, verbose_name='Isiku profiilipilt')),
                ('profiilipilt_organisatsioon', models.BooleanField(default=False, verbose_name='Organisatsiooni profiilipilt')),
                ('profiilipilt_objekt', models.BooleanField(default=False, verbose_name='Objekti profiilipilt')),
                ('inp_date', models.DateTimeField(auto_now_add=True, verbose_name='Lisatud')),
                ('mod_date', models.DateTimeField(auto_now=True, verbose_name='Muudetud')),
                ('artiklid', models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Artikkel', verbose_name='Seotud artiklid')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Lisaja')),
                ('isikud', models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Isik', verbose_name='Seotud isikud')),
                ('kroonikad', models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Kroonika', verbose_name='Seotud allikad')),
                ('objektid', models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Objekt', verbose_name='Seotud objektid')),
                ('organisatsioonid', models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Organisatsioon', verbose_name='Seotud organisatsioonid')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Muutja')),
            ],
            options={
                'verbose_name_plural': 'Pildid',
            },
        ),
    ]
