from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    DailyStressViewSet, TrendAnalysisViewSet,
    CorrelationMatrixViewSet, UserProfileViewSet, HourlyPatternViewSet,
    ModelComparisonViewSet,
)

router = DefaultRouter()
router.register(r'stress', DailyStressViewSet, basename='stress')
router.register(r'trend', TrendAnalysisViewSet, basename='trend')
router.register(r'correlation', CorrelationMatrixViewSet, basename='correlation')
router.register(r'profile', UserProfileViewSet, basename='profile')
router.register(r'hourly', HourlyPatternViewSet, basename='hourly')
router.register(r'model', ModelComparisonViewSet, basename='model')

urlpatterns = [
    path('', include(router.urls)),
]
