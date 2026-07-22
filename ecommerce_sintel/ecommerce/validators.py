import re
from django.core.exceptions import ValidationError


class ComplexPasswordValidator:
    """
    Exige mayuscula + minuscula + numero + caracter especial. Se combina con
    MinimumLengthValidator (min_length=12 en AUTH_PASSWORD_VALIDATORS) para
    cumplir la politica de 12+ caracteres con las 4 clases de caracter.
    """
    UPPER_RE   = re.compile(r'[A-Z]')
    LOWER_RE   = re.compile(r'[a-z]')
    DIGIT_RE   = re.compile(r'[0-9]')
    SPECIAL_RE = re.compile(r'[^A-Za-z0-9]')

    def validate(self, password, user=None):
        errors = []
        if not self.UPPER_RE.search(password):
            errors.append('Debe contener al menos una letra mayuscula.')
        if not self.LOWER_RE.search(password):
            errors.append('Debe contener al menos una letra minuscula.')
        if not self.DIGIT_RE.search(password):
            errors.append('Debe contener al menos un numero.')
        if not self.SPECIAL_RE.search(password):
            errors.append('Debe contener al menos un caracter especial (ej. !@#$%*).')
        if errors:
            raise ValidationError(errors, code='password_no_complexity')

    def get_help_text(self):
        return 'Tu contrasena debe contener al menos una mayuscula, una minuscula, un numero y un caracter especial.'
