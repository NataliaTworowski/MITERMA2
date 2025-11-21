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
        print(f"[API LOGIN] Request recibida desde: {request.META.get('REMOTE_ADDR')}")
        print(f"[API LOGIN] Content-Type: {request.META.get('CONTENT_TYPE')}")
        print(f"[API LOGIN] Method: {request.method}")
        print(f"[API LOGIN] Path: {request.path}")
        
        try:
            print(f"[API LOGIN] Raw body: {request.body}")
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            
            print(f"[API LOGIN] Email recibido: {email}")
            print(f"[API LOGIN] Password length: {len(password) if password else 0}")
            
            if not email or not password:
                print(f"[API LOGIN] Error: Datos incompletos")
                return JsonResponse({
                    'error': 'Datos incompletos',
                    'detail': 'Email y contraseña son requeridos'
                }, status=400)
            
            try:
                print(f"[API LOGIN] Buscando usuario: {email}")
                usuario = Usuario.objects.get(email=email)
                print(f"[API LOGIN] Usuario encontrado: {usuario.nombre}")
                print(f"[API LOGIN] Rol del usuario: {usuario.rol.nombre}")
                print(f"[API LOGIN] Usuario activo: {usuario.is_active}")
                
                if check_password(password, usuario.password):
                    print(f"[API LOGIN] Password válida")
                    # Verificar si es trabajador
                    if usuario.rol.nombre != 'trabajador':
                        print(f"[API LOGIN] Error: Usuario no es trabajador")
                        return JsonResponse({
                            'error': 'Acceso denegado',
                            'detail': 'Solo los trabajadores pueden acceder a la aplicación móvil'
                        }, status=403)
                    
                    print(f"[API LOGIN] Login exitoso")
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
                    print(f"[API LOGIN] Error: Password inválida")
                    return JsonResponse({
                        'error': 'Credenciales inválidas',
                        'detail': 'Email o contraseña incorrectos'
                    }, status=401)
                    
            except Usuario.DoesNotExist:
                print(f"[API LOGIN] Error: Usuario no encontrado")
                return JsonResponse({
                    'error': 'Credenciales inválidas',
                    'detail': 'Email o contraseña incorrectos'
                }, status=401)
                
        except json.JSONDecodeError:
            print(f"[API LOGIN] Error: JSON inválido")
            return JsonResponse({
                'error': 'Datos inválidos',
                'detail': 'El formato de los datos es incorrecto'
            }, status=400)
        except Exception as e:
            print(f"[API LOGIN] Error del servidor: {str(e)}")
            return JsonResponse({
                'error': 'Error del servidor',
                'detail': str(e)
            }, status=500)