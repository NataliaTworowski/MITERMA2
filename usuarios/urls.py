from django.urls import path
from . import views
from . import views_cliente
from . import views_trabajador
from . import views_reportes
from . import views_correos
from . import api

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),
    path('inicio/', views.inicio, name='inicio'),
    path('registro/', views.registro_usuario, name='registro'),
    path('adm_termas/', views.adm_termas, name='adm_termas'),
    path('limpiar-compras-hoy/', views.limpiar_compras_hoy, name='limpiar_compras_hoy'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    path('cambiar-password-temporal/', views.cambiar_password_temporal, name='cambiar_password_temporal'), 
    path('admin_general/', views.admin_general, name='admin_general'),
    path('solicitudes_pendientes/', views.solicitudes_pendientes, name='solicitudes_pendientes'),
    path('mis_entradas/', views_cliente.mostrar_entradas, name='mis_entradas'),
    path('get_qr/<uuid:compra_uuid>/', views_cliente.get_qr_code, name='get_qr_code'),
    path('ocultar_compra/<uuid:compra_uuid>/', views_cliente.ocultar_compra, name='ocultar_compra'),
    path('reenviar_correo/<uuid:compra_uuid>/', views_correos.reenviar_correo_compra, name='reenviar_correo_compra'),
    path('perfil/', views_cliente.perfil_cliente, name='perfil_cliente'),
    path('actualizar_perfil/', views_cliente.actualizar_perfil, name='actualizar_perfil'),
    path('cambiar_contrasena/', views_cliente.cambiar_contrasena, name='cambiar_contrasena'),
    path('favoritos/', views_cliente.favoritos, name='favoritos'),
    path('toggle_favorito/<uuid:terma_uuid>/', views_cliente.toggle_favorito, name='toggle_favorito'),
    path('verificar_favorito/<uuid:terma_uuid>/', views_cliente.verificar_favorito, name='verificar_favorito'),
    path('billetera/', views.billetera, name='billetera'),
    path('historial-entradas/', views.historial_entradas, name='historial_entradas'),
    path('vincular-mercadopago/', views.vincular_mercadopago, name='vincular_mercadopago'),
    path('mercadopago-callback/', views.mercadopago_callback, name='mercadopago_callback'),
    
    # URLs para reportes premium
    path('reportes-premium/', views_reportes.reportes_premium, name='reportes_premium'),
    path('exportar-reporte-csv/', views_reportes.exportar_reporte_csv, name='exportar_reporte_csv'),
    path('exportar-reporte-excel/', views_reportes.exportar_reporte_excel, name='exportar_reporte_excel'),
    path('exportar-reporte-pdf/', views_reportes.exportar_reporte_pdf, name='exportar_reporte_pdf'),
    
    # URLs para trabajadores/operadores
    path('trabajador/', views_trabajador.inicio_trabajador, name='inicio_trabajador'),
    path('escanear-qr/', views_trabajador.escanear_qr, name='escanear_qr'),
    path('buscar-entrada/', views_trabajador.buscar_entrada, name='buscar_entrada'),
    path('registro-entradas/', views_trabajador.registro_entradas_escaneadas, name='registro_entradas_escaneadas'),
    path('perfil-trabajador/', views_trabajador.perfil_trabajador, name='perfil_trabajador'),
    path('actualizar-perfil-trabajador/', views_trabajador.actualizar_perfil_trabajador, name='actualizar_perfil_trabajador'),
    path('cambiar-contrasena-trabajador/', views_trabajador.cambiar_contrasena_trabajador, name='cambiar_contrasena_trabajador'),
    
    # URLs para gestión de termas asociadas (Admin General)
    path('admin/termas-asociadas/', views.admin_general_termas_asociadas, name='admin_general_termas_asociadas'),
    path('admin/crear-terma/', views.admin_general_crear_terma, name='admin_general_crear_terma'),
    path('admin/terma-detalle/<uuid:terma_uuid>/', views.admin_general_terma_detalle, name='admin_general_terma_detalle'),
    path('admin/terma-editar/<uuid:terma_uuid>/', views.admin_general_terma_editar, name='admin_general_terma_editar'),
    path('admin/terma-actualizar/<uuid:terma_uuid>/', views.admin_general_terma_actualizar, name='admin_general_terma_actualizar'),
    path('admin/terma-cambiar-estado/<uuid:terma_uuid>/', views.admin_general_terma_cambiar_estado, name='admin_general_terma_cambiar_estado'),
    path('admin/terma-estadisticas/<uuid:terma_uuid>/', views.admin_general_terma_estadisticas, name='admin_general_terma_estadisticas'),
    
    # URLs para configuración de administrador general
    path('admin/configuracion/', views.configuracion_admin, name='configuracion_admin'),
    path('admin/actualizar-perfil/', views.actualizar_perfil_admin, name='actualizar_perfil_admin'),
    path('admin/cambiar-contrasena/', views.cambiar_contrasena_admin, name='cambiar_contrasena_admin'),
    
    # API endpoints
    path('api/login/', api.LoginAPIView.as_view(), name='api_login'),
    path('api/comunas/<int:region_id>/', views.api_comunas_por_region, name='api_comunas_por_region'),
]