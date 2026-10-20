import secrets
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import OsonInvoice, OsonTerminalTransaction
from .serializers import OsonInvoiceCreateSerializer, OsonInvoiceNotifySerializer, OsonMerchantCheckSerializer, OsonMerchantPaySerializer
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

def verify_oson_token(request):
    received = request.headers.get("token", "")
    expected = settings.OSON_SECRET_TOKEN

    return bool(received) and secrets.compare_digest(received,expected,)


def find_invoice(data):

    invoices = OsonInvoice.objects.filter(user_account=data["account"],merchant_id=data["merchant_id"],)

    if invoices.count() != 1:
        return None

    return invoices.first()



class OsonTerminalCheckAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not verify_oson_token(request):
            return Response({
                "success": False,
                "state": 4,
            })

        serializer = OsonMerchantCheckSerializer(data=request.data,)

        if not serializer.is_valid():
            return Response({
                "success": False,
                "state": -1,
            })

        data = serializer.validated_data
        invoice = find_invoice(data)

        if invoice is None:
            return Response({
                "success": False,
                "state": 3,
            })

        if invoice.status != OsonInvoice.Status.REGISTERED:
            return Response({
                "success": False,
                "state": -1,
            })

        if data["amount"] != invoice.amount:
            return Response({
                "success": False,
                "state": 5,
            })

        return Response({
            "success": True,
            "state": 1,
        })


class OsonTerminalPayAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        if not verify_oson_token(request):
            return Response({"state": -1})

        serializer = OsonMerchantPaySerializer(
            data=request.data,
        )

        if not serializer.is_valid():
            return Response({"state": -1})

        data = serializer.validated_data
        agent_transaction_id = str(data["agent_transaction_id"])

        with transaction.atomic():

            existing = (OsonTerminalTransaction.objects.select_for_update().filter(agent_transaction_id=agent_transaction_id).first())

            if existing is not None:
                if (
                    existing.amount != data["amount"]
                    or existing.invoice.user_account != data["account"]
                    or existing.invoice.merchant_id != data["merchant_id"]
                ):
                    return Response({"state": -1})

                if existing.status == OsonTerminalTransaction.Status.PAID:
                    return Response({
                        "state": 1,
                        "transaction_id": str(existing.pk),
                    })

                return Response({"state": 2})

            invoice = find_invoice(data)

            if invoice is None:
                return Response({"state": -1})

            invoice = (
                OsonInvoice.objects
                .select_for_update()
                .get(pk=invoice.pk)
            )

            if (
                invoice.status != OsonInvoice.Status.REGISTERED
                or invoice.amount != data["amount"]
            ):
                return Response({"state": -1})

            terminal_tx = OsonTerminalTransaction.objects.create(
                agent_transaction_id=agent_transaction_id,
                invoice=invoice,
                amount=data["amount"],
                status=OsonTerminalTransaction.Status.PAID,
            )

            invoice.status = OsonInvoice.Status.PAID
            invoice.save(update_fields=["status", "updated_at"])


            event = {
                "event": "payment.paid",
                "provider": "oson",
                "channel": "terminal",
                "order_id": str(invoice.pk),
                "transaction_id": str(terminal_tx.pk),
                "amount": str(terminal_tx.amount),
                "status": "paid",
                "paid_at": timezone.now().isoformat(),
            }

            def publish_after_commit():
                try:
                    send_payment_event(event)
                except Exception:
                    logger.exception(
                        "Failed to publish OSON Terminal payment event. "
                        "agent_transaction_id=%s",
                        agent_transaction_id,
                    )

            transaction.on_commit(publish_after_commit)


            return Response({
                "state": 1,
                "transaction_id": str(terminal_tx.pk),
            })