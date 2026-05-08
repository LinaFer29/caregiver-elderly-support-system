from django.urls import path, include
from rest_framework import routers
from .views import ActivitiesWithProgramView, AssigmentViewSet, ProgramViewSet

router = routers.DefaultRouter()
router.register(r'programs', ProgramViewSet, 'programs')
router.register(r'assigments', AssigmentViewSet, 'assigments')


urlpatterns = [
    path('', include(router.urls)),
    path('activities-with-program/', ActivitiesWithProgramView.as_view(), name='activities-with-program'),
    path('activities-with-program/<int:activity_id>/',ActivitiesWithProgramView.as_view()),
]