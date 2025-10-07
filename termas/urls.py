from django.urls import path
from . import views, views_admin

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
]