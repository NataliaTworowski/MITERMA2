from django.contrib import admin
from .models import Usuario, Rol, TokenRestablecerContrasena, Favorito

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('email', 'nombre', 'apellido', 'rol', 'estado', 'fecha_registro')
    list_filter = ('rol', 'estado', 'fecha_registro')
    search_fields = ('email', 'nombre', 'apellido')
    ordering = ('-fecha_registro',)


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)


@admin.register(TokenRestablecerContrasena)
class TokenRestablecerContrasenaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'codigo', 'fecha_creacion', 'usado', 'es_valido')
    list_filter = ('usado', 'fecha_creacion')
    search_fields = ('usuario__email', 'codigo')
    readonly_fields = ('token', 'codigo', 'fecha_creacion')


@admin.register(Favorito)
class FavoritoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'terma', 'fecha_agregado')
    list_filter = ('fecha_agregado',)
    search_fields = ('usuario__email', 'usuario__nombre', 'terma__nombre_terma')
    readonly_fields = ('fecha_agregado',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario', 'terma')
