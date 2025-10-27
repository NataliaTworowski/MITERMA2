
from django.shortcuts import render
import mercadopago
from dotenv import load_dotenv
import os
load_dotenv()


def pago(request):
    # Mostrar datos de la compra y preparar integración Mercado Pago
    datos = {}
    if request.method == 'POST':
        access_token = os.getenv("MP_ACCESS_TOKEN")
        sdk = mercadopago.SDK(access_token)
        datos['entrada_id'] = request.POST.get('entrada_id')
        datos['experiencia'] = request.POST.get('input_experiencia')
        datos['precio'] = request.POST.get('input_precio')
        datos['incluidos'] = request.POST.get('input_incluidos')
        datos['extras'] = request.POST.get('input_extras')
        datos['total'] = request.POST.get('input_total')
        datos['cantidad'] = request.POST.get('cantidad')
        datos['fecha'] = request.POST.get('fecha')
        datos['cantidad_entradas'] = request.POST.get('cantidad')

        # Mercado Pago integración
        env_base = os.getenv('MP_BASE_URL')
        if env_base:
            base_url = env_base.rstrip('/')
        else:
            base_url = request.build_absolute_uri('/')[:-1]  # Quita el slash final
        preference_data = {
            "items": [
                {
                    "title": f"Reserva: {datos['experiencia']}",
                    "quantity": int(datos['cantidad_entradas']) if datos['cantidad_entradas'] else 1,
                    "unit_price": float(datos['precio'].replace(',', '.')) if datos['precio'] else 0.0,
                    "currency_id": "CLP"
                }
            ],
            "back_urls": {
                "success": f"{base_url}/ventas/pago/success/",
                "failure": f"{base_url}/ventas/pago/failure/",
                "pending": f"{base_url}/ventas/pago/pending/"
            },
            "auto_return": "approved"
        }
        preference_response = sdk.preference().create(preference_data)
        #print('MP preference response:', preference_response)
        response_data = preference_response.get("response", {})
        if "init_point" in response_data:
            datos['mercadopago_url'] = response_data["init_point"]
        else:
            datos['mercadopago_error'] = response_data.get("message", "No se pudo generar el enlace de pago. Intenta nuevamente.")

    return render(request, 'ventas/pago.html', datos)