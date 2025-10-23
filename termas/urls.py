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
    
    # URL para filtrar comentarios AJAX
    path('comentarios-filtrados/<int:terma_id>/', cargar_comentarios_filtrados, name='comentarios_filtrados'),
    
    # Nuevas rutas
    path('analisis_terma/', views.analisis_terma, name='analisis_terma'),
    path('editar_terma/', views.editar_terma, name='editar_terma'),
    path('agregar_servicio/', views.agregar_servicio, name='agregar_servicio'),
    path('quitar_servicio/<int:servicio_id>/', views.quitar_servicio, name='quitar_servicio'),
]