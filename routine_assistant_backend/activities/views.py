from rest_framework import viewsets
from users.models import Caregiver
from .serializers import ActivitySerializer, CategorySerializer
from .models import Activity, Category
from rest_framework.permissions import IsAuthenticated
# Create your views here.
# ModelViewSet provides default implementations for CRUD operations (Create, Retrieve, Update, Delete) for the specified model.
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.all() #Data that will be used for the viewset
    serializer_class = ActivitySerializer # To convert the model instances to JSON format and vice versa
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.filter(
            program__caregiver__user=self.request.user
        ).distinct()

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Category.objects.filter(
            caregiver__user=self.request.user
        )
    def perform_create(self, serializer):
        caregiver = Caregiver.objects.get(user=self.request.user)
        serializer.save(caregiver=caregiver)