# Generated by Django 5.1.4 on 2025-01-07 19:55

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Jaam',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='Jaam')),
                ('wmocode', models.CharField(blank=True, max_length=10, verbose_name='wmocode')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='longitude')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='latitude')),
            ],
            options={
                'verbose_name_plural': 'Jaamad',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Ilm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('airtemperature', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Õhutemperatuur tunni keskmine (°C)')),
                ('relativehumidity', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Suhteline õhuniiskus (%)')),
                ('airpressure', models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True, verbose_name='Õhurõhk merepinnal (hPa)')),
                ('airpressure_delta', models.DecimalField(blank=True, decimal_places=1, max_digits=6, null=True, verbose_name='Õhurõhu muutus (hPa)')),
                ('winddirection', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Tuul suund (°)')),
                ('windspeed', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Tuul kiirus (m/s)')),
                ('windspeedmax', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Tuul max kiirus (m/s)')),
                ('cloudiness', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Pilvisus (palli)')),
                ('phenomenon', models.CharField(blank=True, max_length=50, null=True, verbose_name='Hetkeilm (sensor)')),
                ('phenomenon_observer', models.CharField(blank=True, max_length=50, null=True, verbose_name='Hetkeilm (vaatleja)')),
                ('precipitations', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Sademed (mm)')),
                ('visibility', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Nähtavus (km)')),
                ('timestamp', models.DateTimeField(blank=True, verbose_name='Mõõtmise aeg')),
                ('airtemperature_max', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Õhutemperatuur tunni max (°C)')),
                ('airtemperature_min', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Õhutemperatuur tunni min (°C)')),
                ('station', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, to='ilm.jaam')),
            ],
            options={
                'verbose_name_plural': 'Ilmavaatlused',
                'ordering': ['-timestamp'],
            },
        ),
    ]
