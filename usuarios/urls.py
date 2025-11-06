from django.urls import path
from . import views
from . import views_cliente
from . import api

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_usuario, name='login'),
    path('login-seguro/', views.login_usuario_nuevo, name='login_seguro'),  # Nueva versión segura
    path('logout/', views.logout_usuario, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('registro/', views.registro_usuario, name='registro'),
    path('adm_termas/', views.adm_termas, name='adm_termas'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'), 
    path('admin_general/', views.admin_general, name='admin_general'),
    path('solicitudes_pendientes/', views.solicitudes_pendientes, name='solicitudes_pendientes'),
    path('mis_entradas/', views_cliente.mostrar_entradas, name='mis_entradas'),
    path('get_qr/<int:compra_id>/', views_cliente.get_qr_code, name='get_qr_code'),
    path('ocultar_compra/<int:compra_id>/', views_cliente.ocultar_compra, name='ocultar_compra'),
    path('billetera/', views.billetera, name='billetera'),
    path('vincular-mercadopago/', views.vincular_mercadopago, name='vincular_mercadopago'),
    path('mercadopago-callback/', views.mercadopago_callback, name='mercadopago_callback'),
    # API endpoints
    path('api/login/', api.LoginAPIView.as_view(), name='api_login'),
]