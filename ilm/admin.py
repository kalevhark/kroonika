from django.contrib import admin

from .models import Jaam, Ilm

class JaamAdmin(admin.ModelAdmin):
    pass

class IlmAdmin(admin.ModelAdmin):
    search_fields = [
        'id',
        'timestamp',
    ]
    list_display = (
        'id',
        'timestamp',
        'airtemperature'
    )
    list_filter = ['timestamp']

admin.site.register(Jaam, JaamAdmin)
admin.site.register(Ilm, IlmAdmin)
