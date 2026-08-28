import hashlib
import hmac

import requests

from django.conf import settings

from .models import OsonInvoice


class OsonService:
    BASE_URL = "https://api.oson.uz/api"

    def __init__(self):
        self.merchant_id = settings.OSON_MERCHANT_ID
        self.secret_token = settings.OSON_SECRET_TOKEN

    @property
    def headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "token": self.secret_token,
        }

    def create_invoice(self,invoice: OsonInvoice):

        url = f"{self.BASE_URL}/invoice/create"

        payload = {
            "merchant_id": self.merchant_id,
            "transaction_id": invoice.transaction_id,
            "phone": invoice.phone,
            "user_account": invoice.user_account,
            "amount": float(invoice.amount),
            "currency": invoice.currency,
            "comment": invoice.comment,
            "return_url": invoice.return_url,
            "lifetime": invoice.lifetime,
            "lang": invoice.lang,
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        invoice.bill_id = data.get("bill_id")
        invoice.pay_url = data.get("pay_url", "")
        invoice.status = data.get(
            "status",
            OsonInvoice.Status.REGISTERED,
        )
        invoice.error_code = data.get(
            "error_code",
            0,
        )
        invoice.message = data.get(
            "message",
            "",
        )

        invoice.save(
            update_fields=[
                "bill_id",
                "pay_url",
                "status",
                "error_code",
                "message",
                "updated_at",
            ],
        )

        return data

    def get_invoice_status(
        self,
        transaction_id: str,
    ):
        url = f"{self.BASE_URL}/invoice/status"

        payload = {
            "merchant_id": self.merchant_id,
            "transaction_id": transaction_id,
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    def verify_signature(
        self,
        transaction_id: str,
        bill_id: int,
        status: str,
        signature: str,
    ) -> bool:
        parameters = (
            f"{transaction_id}:{bill_id}:{status}"
        )

        first_hash = hashlib.sha256(
            f"{self.secret_token}:{self.merchant_id}".encode()
        ).hexdigest()

        expected_signature = hashlib.sha256(
            f"{first_hash}:{parameters}".encode()
        ).hexdigest()

        return hmac.compare_digest(
            expected_signature,
            signature,
        )