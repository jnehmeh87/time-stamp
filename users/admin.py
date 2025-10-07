from django.contrib import admin
from .models import CustomUser, Organization, Membership

class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'country', 'is_staff')
    inlines = (MembershipInline,)

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name',)
    inlines = (MembershipInline,)

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role')
    list_filter = ('organization', 'role')
