from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = routers.DefaultRouter()
router.register(r'caregivers', views.CaregiverViewSet, 'caregivers')
router.register(r'elderly', views.ElderlyViewSet, 'elderly')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', views.RegisterUserView.as_view(), name='register-user'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]