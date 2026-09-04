from rest_framework import serializers
from .models import (DailyStress, TrendAnalysis, CorrelationMatrix, UserProfile,
                     HourlyPattern, ClassificationResult, FeatureImportance,
                     ModelMetrics, LearningCurve)


class DailyStressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStress
        fields = '__all__'


class TrendAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrendAnalysis
        fields = '__all__'


class CorrelationMatrixSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrelationMatrix
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'


class HourlyPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourlyPattern
        fields = '__all__'


class ClassificationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassificationResult
        fields = '__all__'


class FeatureImportanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureImportance
        fields = '__all__'


class ModelMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetrics
        fields = '__all__'


class LearningCurveSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningCurve
        fields = '__all__'
