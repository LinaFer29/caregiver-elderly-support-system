from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('caregiver', 'Caregiver'),
        ('elderly', 'Elderly'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)


class Caregiver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    caregiver_type = models.CharField(max_length=100)

    def __str__(self):
        return self.user.username


class Elderly(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    age = models.PositiveIntegerField(null=True, blank=True)
    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE, related_name='elderlies')
    relationship_to_caregiver = models.CharField(max_length=100)
    dependency_level = models.CharField(max_length=100)
    underlying_conditions = models.TextField()

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip() or f"Elderly {self.pk}"
