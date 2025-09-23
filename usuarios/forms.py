from django import forms
from django.contrib.auth.models import User

class UsuarioForm(forms.ModelForm):
    """Formulario para usuarios."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']