from django.urls import path
from . import views, views_admin
from usuarios.views import cargar_comentarios_filtrados

app_name = 'termas'

urlpatterns = [
    path('', views.lista_termas, name='lista'),
    path('detalle/<int:pk>/', views.detalle_terma, name='detalle'),
    path('buscar/', views.buscar_termas, name='buscar'),
    path('subir-fotos/', views.subir_fotos, name='subir_fotos'),
    path('eliminar-foto/<int:foto_id>/', views.eliminar_foto, name='eliminar_foto'),
    
    # URLs de administración
    path('aprobar_solicitud/<int:solicitud_id>/', views_admin.aprobar_solicitud, name='aprobar_solicitud'),
    path('rechazar_solicitud/<int:solicitud_id>/', views_admin.rechazar_solicitud, name='rechazar_solicitud'),
    path('detalles_solicitud/<int:solicitud_id>/', views_admin.detalles_solicitud, name='detalles_solicitud'),
    
    # URLs de administración de pagos
    path('admin/distribuciones-pago/', views_admin.ver_distribuciones_pago, name='ver_distribuciones_pago'),
    path('admin/reporte-comisiones-diarias/', views_admin.reporte_comisiones_diarias, name='reporte_comisiones_diarias'),
    path('admin/detalle-distribucion/<int:distribucion_id>/', views_admin.ver_detalle_distribucion, name='ver_detalle_distribucion'),
    
    # URL para filtrar comentarios AJAX
    path('comentarios-filtrados/<int:terma_id>/', cargar_comentarios_filtrados, name='comentarios_filtrados'),
    
    # Nuevas rutas
    path('analisis_terma/', views.analisis_terma, name='analisis_terma'),
    path('editar_terma/', views.editar_terma, name='editar_terma'),
    path('agregar_servicio/', views.agregar_servicio, name='agregar_servicio'),
    path('editar_servicio/<int:servicio_id>/', views.editar_servicio, name='editar_servicio'),
    path('quitar_servicio/<int:servicio_id>/', views.quitar_servicio, name='quitar_servicio'),
    path('precios_terma/', views.precios_terma, name='precios_terma'),
    path('crear_entrada/', views.crear_entrada, name='crear_entrada'),
    path('gestionar_servicios_entrada/<int:entrada_id>/', views.gestionar_servicios_entrada, name='gestionar_servicios_entrada'),
    path('editar_entrada/<int:entrada_id>/', views.editar_entrada, name='editar_entrada'),
    path('eliminar_entrada/<int:entrada_id>/', views.eliminar_entrada, name='eliminar_entrada'),
    path('calendario_termas/', views.calendario_termas, name='calendario_termas'),
    path('vista_termas/', views.vista_termas, name='vista_termas'),
    path('comprar/<int:terma_id>/', views.vista_terma, name='vista_terma'),
    path('suscripcion/', views.suscripcion, name='suscripcion'),
    path('cambiar_suscripcion/', views.cambiar_suscripcion, name='cambiar_suscripcion'),
    
    # URLs para distribuciones de pago
    path('admin/distribuciones-pago/', views_admin.ver_distribuciones_pago, name='admin_distribuciones_pago'),
    path('admin/reporte-comisiones-diarias/', views_admin.reporte_comisiones_diarias, name='admin_reporte_comisiones'),
    path('dashboard-comisiones/<int:terma_id>/', views_admin.dashboard_comisiones_terma, name='dashboard_comisiones'),
]