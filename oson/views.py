from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import OsonInvoice
from .serializers import OsonInvoiceCreateSerializer , OsonInvoiceNotifySerializer
from .services import OsonService
from config import settings
from .kafka_send import send_payment_event
from django.db import transaction
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

class OsonInvoiceCreateAPIView(APIView):

    def post(self, request):
        serializer = OsonInvoiceCreateSerializer(data=request.data,)
        serializer.is_valid(raise_exception=True,)
        invoice = OsonInvoice.objects.create(
            merchant_id=settings.OSON_MERCHANT_ID,
            **serializer.validated_data,
        )
        service = OsonService()
        data = service.create_invoice(invoice=invoice,)

        return Response(
            data,
            status=status.HTTP_201_CREATED,
        )




class OsonInvoiceNotifyAPIView(APIView):

    def post(self, request):
        serializer = OsonInvoiceNotifySerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        payment_status = str(data["status"]).strip().upper()

        service = OsonService()

        is_valid = service.verify_signature(
            transaction_id=data["transaction_id"],
            bill_id=data["bill_id"],
            status=data["status"],
            signature=data["signature"],
        )

        if not is_valid:
            logger.warning(
                "Invalid Oson signature: transaction_id=%s",
                data["transaction_id"],
            )
            return Response(
                {"detail": "Invalid signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invoice = get_object_or_404(
                OsonInvoice.objects.select_for_update(),
                transaction_id=data["transaction_id"],
            )

            already_paid = (
                str(invoice.status).strip().upper() == "PAID"
            )

            invoice.bill_id = data["bill_id"]
            invoice.status = payment_status

            invoice.save(
                update_fields=[
                    "bill_id",
                    "status",
                    "updated_at",
                ],
            )

            if payment_status == "PAID" and not already_paid:
                event = {
                    "event": "payment.paid",
                    "provider": "oson",
                    "order_id": str(invoice.id),
                    "transaction_id": str(data["transaction_id"]),
                    "bill_id": str(data["bill_id"]),
                    "status": "paid",
                    "paid_at": timezone.localtime(timezone.now()).isoformat(),
                }

                def publish_after_commit(event=event):
                    try:
                        send_payment_event(event)
                    except Exception:
                        logger.exception(
                            "Failed to publish Oson payment event: "
                            "transaction_id=%s",
                            data["transaction_id"],
                        )

                transaction.on_commit(publish_after_commit)

        return Response(
            {"success": True},
            status=status.HTTP_200_OK,
        )