from django.contrib import admin
from .models import Client

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'phone', 'email', 'created_at')
    search_fields = ('name', 'company', 'phone', 'email')
    list_filter = ('company',)
