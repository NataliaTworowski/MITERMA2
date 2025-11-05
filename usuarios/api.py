from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import check_password
import json
from .models import Usuario

@method_decorator(csrf_exempt, name='dispatch')
class LoginAPIView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            
            if not email or not password:
                return JsonResponse({
                    'error': 'Datos incompletos',
                    'detail': 'Email y contraseña son requeridos'
                }, status=400)
            
            try:
                usuario = Usuario.objects.get(email=email)
                
                if check_password(password, usuario.password):
                    # Verificar si es trabajador
                    if usuario.rol.nombre != 'trabajador':
                        return JsonResponse({
                            'error': 'Acceso denegado',
                            'detail': 'Solo los trabajadores pueden acceder a la aplicación móvil'
                        }, status=403)
                    
                    return JsonResponse({
                        'success': True,
                        'user': {
                            'id': usuario.id,
                            'nombre': usuario.nombre,
                            'email': usuario.email,
                            'rol': usuario.rol.nombre
                        }
                    })
                else:
                    return JsonResponse({
                        'error': 'Credenciales inválidas',
                        'detail': 'Email o contraseña incorrectos'
                    }, status=401)
                    
            except Usuario.DoesNotExist:
                return JsonResponse({
                    'error': 'Credenciales inválidas',
                    'detail': 'Email o contraseña incorrectos'
                }, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Datos inválidos',
                'detail': 'El formato de los datos es incorrecto'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'error': 'Error del servidor',
                'detail': str(e)
            }, status=500)