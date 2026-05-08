from django.contrib import admin

from .models import Caregiver, Elderly, User

# Register your models here.
admin.site.register(User)
admin.site.register(Caregiver)
admin.site.register(Elderly)
