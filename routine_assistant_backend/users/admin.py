from django.contrib import admin

from .models import Caregiver, Elderly, User

admin.site.register(User)


@admin.register(Elderly)
class ElderlyAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "age",
        "caregiver",
        "relationship_to_caregiver",
        "dependency_level",
    )
    search_fields = ("first_name", "last_name", "relationship_to_caregiver")
    list_filter = ("dependency_level", "caregiver")


@admin.register(Caregiver)
class CaregiverAdmin(admin.ModelAdmin):
    list_display = ("user", "caregiver_type")
    search_fields = ("user__username", "user__email", "caregiver_type")
