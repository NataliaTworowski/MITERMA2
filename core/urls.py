from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'), 
    path('mostrar_termas/', views.mostrar_termas, name='mostrar_termas')
]+ static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])