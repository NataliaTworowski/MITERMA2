from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.lista_ventas, name='lista'),
    path('nueva/', views.nueva_venta, name='nueva'),
]