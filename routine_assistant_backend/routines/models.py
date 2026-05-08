from django.db import models

# Create your models here.
from django.db import models
from activities.models import Activity
from users.models import Caregiver, Elderly

class Program(models.Model):
    caregiver = models.ForeignKey(Caregiver, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)

    date = models.DateField()
    time = models.TimeField()

    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ]

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.activity.title} - {self.date} {self.time}"


class Assignment(models.Model):
    elderly = models.ForeignKey(Elderly, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)

    date = models.DateField()
    notification_time = models.TimeField()

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    response_time = models.TimeField(null=True, blank=True)
    user_response = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.activity.title} - {self.status}"