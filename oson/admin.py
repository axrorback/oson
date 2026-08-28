from django.contrib import admin
from .models import OsonInvoice


@admin.register(OsonInvoice)
class OsonInvoiceAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "status")