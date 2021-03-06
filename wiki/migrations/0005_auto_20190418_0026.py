# Generated by Django 2.2 on 2019-04-17 21:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wiki', '0004_pilt'),
    ]

    operations = [
        migrations.CreateModel(
            name='Allikas',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nimi', models.CharField(max_length=100, verbose_name='Allikas')),
                ('kirjeldus', models.TextField(blank=True, null=True, verbose_name='Kirjeldus')),
                ('url', models.URLField(blank=True, verbose_name='Internet')),
                ('inp_date', models.DateTimeField(auto_now_add=True, verbose_name='Lisatud')),
                ('mod_date', models.DateTimeField(auto_now=True, verbose_name='Muudetud')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Lisaja')),
                ('updated_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Muutja')),
            ],
            options={
                'verbose_name': 'Allikas',
                'verbose_name_plural': 'Allikad',
            },
        ),
        migrations.AlterModelOptions(
            name='kroonika',
            options={'verbose_name': 'Kroonika', 'verbose_name_plural': 'Kroonikad'},
        ),
        migrations.RemoveField(
            model_name='pilt',
            name='kroonikad',
        ),
        migrations.RemoveField(
            model_name='pilt',
            name='profiilipilt_kroonika',
        ),
        migrations.AddField(
            model_name='pilt',
            name='profiilipilt_allikas',
            field=models.BooleanField(default=False, verbose_name='Allika profiilipilt'),
        ),
        migrations.AlterField(
            model_name='artikkel',
            name='kroonika',
            field=models.ForeignKey(blank=True, help_text='Kroonika', null=True, on_delete=django.db.models.deletion.SET_NULL, to='wiki.Kroonika', verbose_name='Kroonika'),
        ),
        migrations.AlterField(
            model_name='kroonika',
            name='nimi',
            field=models.CharField(max_length=100, verbose_name='Kroonika'),
        ),
        migrations.CreateModel(
            name='Viide',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('marker', models.CharField(blank=True, max_length=10, verbose_name='Marker')),
                ('hist_date', models.DateField(blank=True, help_text='Avaldatud', null=True, verbose_name='Avaldatud')),
                ('hist_year', models.IntegerField(blank=True, help_text='Avaldamise aasta', null=True, verbose_name='Avaldatud')),
                ('kohaviit', models.CharField(blank=True, max_length=50, null=True, verbose_name='Viit')),
                ('url', models.URLField(blank=True, verbose_name='Internet')),
                ('mod_date', models.DateTimeField(auto_now=True, verbose_name='Kasutatud')),
                ('allikas', models.ForeignKey(blank=True, help_text='Allikas', null=True, on_delete=django.db.models.deletion.SET_NULL, to='wiki.Allikas', verbose_name='Allikas')),
            ],
        ),
        migrations.AddField(
            model_name='artikkel',
            name='viited',
            field=models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Viide', verbose_name='Viited'),
        ),
        migrations.AddField(
            model_name='isik',
            name='viited',
            field=models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Viide', verbose_name='Viited'),
        ),
        migrations.AddField(
            model_name='objekt',
            name='viited',
            field=models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Viide', verbose_name='Viited'),
        ),
        migrations.AddField(
            model_name='organisatsioon',
            name='viited',
            field=models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Viide', verbose_name='Viited'),
        ),
        migrations.AddField(
            model_name='pilt',
            name='allikad',
            field=models.ManyToManyField(blank=True, help_text='Mitme valimiseks hoia all <Ctrl> klahvi', to='wiki.Allikas', verbose_name='Seotud allikad'),
        ),
    ]
