from django.urls import path, include
from rest_framework.documentation import include_docs_urls
from rest_framework import routers
from activities import views

#Generación de rutas (GET, POST, PUT, DELETE) para la API utilizando el router de Django REST Framework
router = routers.DefaultRouter()
router.register(r'activities', views.ActivityViewSet, 'activities')
router.register(r'categories', views.CategoryViewSet, 'categories')

urlpatterns = [
    path('', include(router.urls)),
    path('docs/app/activities', include_docs_urls(title='Routine Assistant API', description='API documentation for the Routine Assistant application.')),
]