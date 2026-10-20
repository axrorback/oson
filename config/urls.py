
from django.contrib import admin
from django.urls import path , include
from oson.views import OsonTerminalCheckAPIView , OsonTerminalPayAPIView
urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/oson/", include("oson.urls")),
    path('api/payment/check/', OsonTerminalCheckAPIView.as_view()),
    path('api/payment/pay/', OsonTerminalPayAPIView.as_view()),

]
