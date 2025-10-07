from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'), 
    path('mostrar_termas/', views.mostrar_termas, name='mostrar_termas'),
    path('planes/', views.planes, name='planes'),
    path('solicitud_terma/', views.planes, name='solicitud_terma'),
    path('api/comunas/<int:region_id>/', views.get_comunas, name='get_comunas'),
]+ static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])