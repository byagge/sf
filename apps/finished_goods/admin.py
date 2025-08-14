from django.contrib import admin
from .models import FinishedGood

@admin.register(FinishedGood)
class FinishedGoodAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity', 'order', 'status', 'received_at', 'issued_at', 'recipient')
    list_filter = ('status', 'product', 'order', 'received_at', 'issued_at')
    search_fields = ('product__name', 'order__name', 'recipient', 'comment')
    readonly_fields = ('received_at', 'issued_at')
