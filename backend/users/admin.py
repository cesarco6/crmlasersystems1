# users/admin.py
from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rol')
    list_filter = ('rol',)
    search_fields = ('user__username',)


