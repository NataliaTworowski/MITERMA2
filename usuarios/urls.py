from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_usuario, name='login'),
    path('inicio/', views.inicio, name='inicio'),
    path('registro/', views.registro_usuario, name='registro'),
]