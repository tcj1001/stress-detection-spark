from django.db import models


class DailyStress(models.Model):
    user_id = models.BigIntegerField()
    activity_date = models.DateField()
    stress_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    risk_level = models.CharField(max_length=10, null=True)
    hr_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    sleep_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    active_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    sedentary_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    trend_label = models.CharField(max_length=20, null=True)
    score_7day_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = 't_daily_stress'
        ordering = ['user_id', 'activity_date']


class TrendAnalysis(models.Model):
    user_id = models.BigIntegerField()
    activity_date = models.DateField()
    stress_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    score_7day_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    score_change_rate = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    trend_label = models.CharField(max_length=20, null=True)

    class Meta:
        managed = False
        db_table = 't_trend_analysis'
        ordering = ['user_id', 'activity_date']


class CorrelationMatrix(models.Model):
    feature_x = models.CharField(max_length=50)
    feature_y = models.CharField(max_length=50)
    corr_value = models.DecimalField(max_digits=6, decimal_places=4, null=True)

    class Meta:
        managed = False
        db_table = 't_correlation_matrix'


class UserProfile(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    cluster_id = models.IntegerField(null=True)
    cluster_label = models.CharField(max_length=20, null=True)
    avg_stress_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    avg_sleep_efficiency = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    avg_active_minutes = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    avg_resting_hr = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    avg_sedentary_ratio = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    risk_level = models.CharField(max_length=10, null=True)

    class Meta:
        managed = False
        db_table = 't_user_profile'


class HourlyPattern(models.Model):
    user_id = models.BigIntegerField()
    hour_of_day = models.IntegerField()
    avg_intensity = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    avg_calories = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    avg_steps = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    record_count = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = 't_hourly_pattern'
        ordering = ['user_id', 'hour_of_day']


class ClassificationResult(models.Model):
    model_name = models.CharField(max_length=50)
    user_id = models.BigIntegerField()
    activity_date = models.DateField()
    actual_risk = models.CharField(max_length=10, null=True)
    predicted_risk = models.CharField(max_length=10, null=True)
    prediction_correct = models.IntegerField(null=True)
    probability_high = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    probability_medium = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    probability_low = models.DecimalField(max_digits=6, decimal_places=4, null=True)

    class Meta:
        managed = False
        db_table = 't_classification_result'
        ordering = ['user_id', 'activity_date']


class FeatureImportance(models.Model):
    model_name = models.CharField(max_length=50)
    feature_name = models.CharField(max_length=50)
    importance = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    rank_order = models.IntegerField(null=True)

    class Meta:
        managed = False
        db_table = 't_feature_importance'


class ModelMetrics(models.Model):
    model_name = models.CharField(max_length=50)
    metric_name = models.CharField(max_length=50)
    metric_value = models.DecimalField(max_digits=10, decimal_places=6, null=True)

    class Meta:
        managed = False
        db_table = 't_model_metrics'


class LearningCurve(models.Model):
    model_name = models.CharField(max_length=50)
    train_size = models.IntegerField()
    train_score = models.DecimalField(max_digits=8, decimal_places=6, null=True)
    test_score = models.DecimalField(max_digits=8, decimal_places=6, null=True)

    class Meta:
        managed = False
        db_table = 't_learning_curve'
