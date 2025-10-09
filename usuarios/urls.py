from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('registro/', views.registro_usuario, name='registro'),
    path('adm_termas/', views.adm_termas, name='adm_termas'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),  # Sin token
    path('admin_general/', views.admin_general, name='admin_general'),
    path('solicitudes_pendientes/', views.solicitudes_pendientes, name='solicitudes_pendientes'),
]