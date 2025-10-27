from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('pago/', views.pago, name='pago'),
]