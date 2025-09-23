from django.urls import path
from . import views

app_name = 'entradas'

urlpatterns = [
    path('', views.lista_entradas, name='lista'),
    path('nueva/', views.nueva_entrada, name='nueva'),
]