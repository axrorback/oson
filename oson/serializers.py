from rest_framework import serializers

from .models import OsonInvoice


class OsonInvoiceCreateSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = OsonInvoice
        fields = (
            "transaction_id",
            "merchant_id",
            "phone",
            "user_account",
            "amount",
            "currency",
            "comment",
            "return_url",
            "lifetime",
            "lang",
        )

    def validate_currency(self, value):
        if value != "UZS":
            raise serializers.ValidationError(
                "Only UZS currency is supported.",
            )

        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be greater than zero.",
            )

        return value


class OsonInvoiceNotifySerializer(serializers.Serializer):

    status = serializers.CharField()
    transaction_id = serializers.CharField(max_length=36,)
    bill_id = serializers.IntegerField()
    signature = serializers.CharField()


class OsonInvoiceStatusSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(max_length=36)



class OsonMerchantCheckSerializer(serializers.Serializer):
    method = serializers.CharField()
    merchant_id = serializers.IntegerField()
    account = serializers.CharField()
    agent_transaction_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12,decimal_places=2,)
    params = serializers.JSONField(required=False,default=dict)

    def validate_method(self, value):
        if value != "check":
            raise serializers.ValidationError(
                "Invalid method.",
            )

        return value


class OsonMerchantPaySerializer(serializers.Serializer):
    method = serializers.CharField()
    merchant_id = serializers.IntegerField()
    account = serializers.CharField()
    agent_transaction_id = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12,decimal_places=2,)
    params = serializers.JSONField(required=False,default=dict)

    def validate_method(self, value):
        if value != "pay":
            raise serializers.ValidationError(
                "Invalid method.",
            )

        return value
