from django.urls import path
from .views import OsonInvoiceCreateAPIView , OsonInvoiceNotifyAPIView

urlpatterns = [
    path("create/", OsonInvoiceCreateAPIView.as_view(), name="create_invoice"),
    path("notify/", OsonInvoiceNotifyAPIView.as_view(), name="notify_invoice"),
]