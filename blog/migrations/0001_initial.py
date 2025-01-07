# Generated by Django 4.1.5 on 2023-03-16 09:09

from django.db import migrations, models
import django.db.models.deletion
import markdownx.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
            options={
                'verbose_name_plural': 'Teemad',
            },
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('body', markdownx.models.MarkdownxField()),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('categories', models.ManyToManyField(related_name='posts', to='blog.category')),
            ],
            options={
                'verbose_name_plural': 'Postitused',
                'ordering': ['-created_on'],
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('author', models.CharField(max_length=60)),
                ('body', models.TextField()),
                ('remote_addr', models.CharField(blank=True, max_length=40, verbose_name='IP aadress')),
                ('http_user_agent', models.CharField(blank=True, max_length=200, verbose_name='Veebilehitseja')),
                ('inp_date', models.DateTimeField(auto_now_add=True, verbose_name='Lisatud')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='blog.post')),
            ],
            options={
                'verbose_name_plural': 'Kommentaarid',
            },
        ),
    ]
