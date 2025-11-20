from django.urls import path
from . import views
from . import error_views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'), 
    path('mostrar_termas/', views.mostrar_termas, name='mostrar_termas'),
    path('planes/', views.planes, name='planes'),
    path('solicitud_terma/', views.solicitud_terma, name='solicitud_terma'),
    path('api/comunas/<int:region_id>/', views.get_comunas, name='get_comunas'),
    
    # Vistas de error personalizadas (para uso programático)
    path('error/', error_views.custom_error_page, name='custom_error'),
    
    # URLs para probar páginas de error en desarrollo
    path('test-404/', error_views.error_404, name='test_404'),
    path('test-500/', error_views.error_500, name='test_500'),
    path('test-403/', error_views.error_403, name='test_403'),
    path('test-400/', error_views.error_400, name='test_400'),
]+ static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])