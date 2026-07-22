from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PhoneOtp
from .forms import CustomUserCreationForm, CustomUserChangeForm
from accounts.models import UserProfile, TechnicianProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfil personal'
    extra = 0
    fields = (
        'first_name', 'last_name', 'phone_number', 'document',
        'user_type', 'company', 'position',
        'address', 'city', 'state', 'country', 'postal_code',
        'profile_picture',
    )
    # user_type de solo lectura: el UNICO camino autorizado para cambiarlo es
    # KycCommands._apply_requested_user_type() (aprobacion de un upgrade via
    # /panel/validaciones) -- este admin nativo de Django no pasaba por
    # AccountCommands/KycCommands ni dejaba rastro en UserAuditLog, un
    # segundo camino de escritura sin auditar. Ver accounts/CLAUDE.md.
    readonly_fields = ('user_type',)


class TechnicianProfileInline(admin.StackedInline):
    model = TechnicianProfile
    can_delete = True
    verbose_name_plural = 'Perfil de tecnico'
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    ordering = ['-created_at']
    list_display = ('email', 'is_staff', 'is_superuser', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_verified')

    readonly_fields = ('last_login', 'date_joined', 'created_at', 'updated_at')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

    search_fields = ('email',)
    inlines = (UserProfileInline, TechnicianProfileInline)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(PhoneOtp)
class PhoneOtpAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'otp', 'is_verified', 'created_at')
    list_filter = ('is_verified',)
    search_fields = ('phone_number',)
