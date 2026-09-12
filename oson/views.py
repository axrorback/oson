from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import OsonInvoice
from .serializers import OsonInvoiceCreateSerializer , OsonInvoiceNotifySerializer
from .services import OsonService


class OsonInvoiceCreateAPIView(APIView):

    def post(self, request):
        serializer = OsonInvoiceCreateSerializer(data=request.data,)
        serializer.is_valid(raise_exception=True,)
        invoice = OsonInvoice.objects.create(**serializer.validated_data)
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

        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data

        invoice = get_object_or_404(
            OsonInvoice,
            transaction_id=data["transaction_id"],
        )

        service = OsonService()

        is_valid = service.verify_signature(
            transaction_id=data["transaction_id"],
            bill_id=data["bill_id"],
            status=data["status"],
            signature=data["signature"],
        )

        if not is_valid:
            return Response(
                {
                    "detail": "Invalid signature.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoice.bill_id = data["bill_id"]
        invoice.status = data["status"]

        invoice.save(
            update_fields=[
                "bill_id",
                "status",
                "updated_at",
            ],
        )
        service.post_callback_url(invoice=invoice)

        return Response(
            {
                "success": True,
            },
            status=status.HTTP_200_OK,
        )

