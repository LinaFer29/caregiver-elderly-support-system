from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

router = routers.DefaultRouter()
router.register(r'caregivers', views.CaregiverViewSet, 'caregivers')
router.register(r'elderly', views.ElderlyViewSet, 'elderly')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RegisterUserView.as_view(), name='register-user'),
    path('login/', views.CustomLoginView.as_view(), name='custom-login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', views.MeView.as_view(), name='me'),
]
