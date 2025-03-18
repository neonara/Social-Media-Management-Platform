from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User

class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('email', 'first_name', 'last_name', 'is_administrator', 'is_moderator', 'is_community_manager', 'is_client', 'is_active')
    list_filter = ('is_administrator', 'is_moderator', 'is_community_manager', 'is_client', 'is_active')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_administrator', 'is_moderator', 'is_community_manager', 'is_client', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_administrator', 'is_moderator', 'is_community_manager', 'is_client')}
        ),
    )

    search_fields = ('email',)
    ordering = ('email',)  
    filter_horizontal = ()


admin.site.unregister(Group)


admin.site.register(User, UserAdmin)
