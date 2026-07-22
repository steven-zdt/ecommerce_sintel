from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    """
    Formulario de creacion de usuario en el Admin de Django.
    Usa email como USERNAME_FIELD. Los datos personales van en UserProfile (accounts).
    """
    class Meta:
        model = User
        fields = ('email', 'is_staff', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'username' in self.fields:
            del self.fields['username']


class CustomUserChangeForm(UserChangeForm):
    """Formulario de edicion de usuario en el Admin de Django."""
    class Meta:
        model = User
        fields = ('email', 'is_active', 'is_staff', 'is_superuser', 'is_verified')
