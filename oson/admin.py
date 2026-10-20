from django.contrib import admin
from .models import OsonInvoice , OsonTerminalTransaction


@admin.register(OsonInvoice)
class OsonInvoiceAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", 'amount',"status","updated_at",)


@admin.register(OsonTerminalTransaction)
class OsonTerminalTransactionAdmin(admin.ModelAdmin):
    list_display = ("agent_transaction_id",  "amount", "status","updated_at")
