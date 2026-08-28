import uuid

from django.db import models


class OsonInvoice(models.Model):
    class Status(models.TextChoices):
        REGISTERED = "REGISTRED", "Registered"
        PAID = "PAID", "Paid"
        DECLINED = "DECLINED", "Declined"
        ON_PROGRESS = "ON_PROGRESS", "On progress"
        PAY_ERROR = "PAY_ERROR", "Pay error"
        EXPIRED = "EXPIRED", "Expired"
        RETURNED = "RETURNED", "Returned"

    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False,)
    transaction_id = models.CharField(max_length=36,unique=True,null=True,blank=True)
    merchant_id = models.PositiveIntegerField()
    bill_id = models.BigIntegerField(null=True,blank=True,)
    phone = models.CharField(max_length=32,)
    user_account = models.CharField(max_length=36,)
    amount = models.DecimalField(max_digits=12,decimal_places=2,)
    currency = models.CharField(max_length=3,default="UZS",)
    comment = models.CharField(max_length=255,blank=True,)
    return_url = models.URLField(blank=True,)
    lifetime = models.PositiveIntegerField(default=10,)
    lang = models.CharField(max_length=2,default="uz",)
    status = models.CharField(max_length=32,choices=Status,default=Status.REGISTERED,)
    pay_url = models.URLField(blank=True,)
    error_code = models.IntegerField(default=0,)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.transaction_id