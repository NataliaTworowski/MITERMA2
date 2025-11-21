from django.urls import path
from . import views
from . import api
from . import api_disponibilidad

app_name = 'ventas'

urlpatterns = [
    # API endpoints
    path('api/validar-qr/', api.ValidarEntradaQRView.as_view(), name='validar_qr'),
    path('api/debug-qr-usado/', api.DebugQRUsadoView.as_view(), name='debug_qr_usado'),  # Nueva vista de debug
    
    # APIs de disponibilidad
    path('api/disponibilidad/', api_disponibilidad.VerificarDisponibilidadView.as_view(), name='verificar_disponibilidad'),
    path('api/termas-disponibles/', api_disponibilidad.TermasDisponiblesView.as_view(), name='termas_disponibles'),
    path('api/limpiar-compras-vencidas/', api_disponibilidad.limpiar_compras_vencidas_api, name='limpiar_compras_vencidas'),
    path('api/estadisticas-disponibilidad/', api_disponibilidad.estadisticas_disponibilidad, name='estadisticas_disponibilidad'),
    
    path('pago/<uuid:terma_uuid>/', views.pago, name='pago'),
    path('pago/success/', views.pago_exitoso, name='pago_exitoso'),
    path('pago/failure/', views.pago_fallido, name='pago_fallido'),
    path('pago/pending/', views.pago_pendiente, name='pago_pendiente'),
    path('webhook/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),
]