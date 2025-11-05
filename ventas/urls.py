from django.urls import path
from . import views
from . import api

app_name = 'ventas'

urlpatterns = [
    # API endpoints
    path('api/validar-qr/', api.ValidarEntradaQRView.as_view(), name='validar_qr'),
    
    path('pago/<int:terma_id>/', views.pago, name='pago'),
    path('pago/success/', views.pago_exitoso, name='pago_exitoso'),
    path('pago/failure/', views.pago_fallido, name='pago_fallido'),
    path('pago/pending/', views.pago_pendiente, name='pago_pendiente'),
    path('webhook/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),
]