from django.db import models
from users.models import Caregiver

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, default="#000000") # ej: "#FF5733"
    icon = models.CharField(max_length=50, blank=True, default="tags") # ej: "home"
    caregiver = models.ForeignKey(
        Caregiver,
        on_delete=models.CASCADE,
        related_name='categories'
    )
    
    def __str__(self):
        return self.name

class Activity(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.title