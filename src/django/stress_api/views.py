import numpy as np
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count
from .models import (DailyStress, TrendAnalysis, CorrelationMatrix, UserProfile,
                     HourlyPattern, ClassificationResult, FeatureImportance,
                     ModelMetrics, LearningCurve)
from .serializers import (
    DailyStressSerializer, TrendAnalysisSerializer,
    CorrelationMatrixSerializer, UserProfileSerializer, HourlyPatternSerializer,
    ClassificationResultSerializer, ModelMetricsSerializer, LearningCurveSerializer,
)


class DailyStressViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DailyStressSerializer

    def get_queryset(self):
        qs = DailyStress.objects.all()
        user_id = self.request.query_params.get('user_id')
        start = self.request.query_params.get('start_date')
        end = self.request.query_params.get('end_date')
        risk = self.request.query_params.get('risk_level')
        if user_id:
            qs = qs.filter(user_id=user_id)
        if start:
            qs = qs.filter(activity_date__gte=start)
        if end:
            qs = qs.filter(activity_date__lte=end)
        if risk:
            qs = qs.filter(risk_level=risk)
        return qs

    @action(detail=False, methods=['get'], url_path='chart')
    def chart(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        records = DailyStress.objects.filter(user_id=user_id).order_by('activity_date')
        return Response({
            'dates': [str(r.activity_date) for r in records],
            'stress_score': [float(r.stress_score) if r.stress_score else None for r in records],
            'score_7day_avg': [float(r.score_7day_avg) if r.score_7day_avg else None for r in records],
        })

    @action(detail=False, methods=['get'], url_path='risk-summary')
    def risk_summary(self, request):
        data = (DailyStress.objects.values('risk_level')
                .annotate(count=Count('id'))
                .order_by('risk_level'))
        return Response(list(data))

    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request):
        ids = DailyStress.objects.values_list('user_id', flat=True).distinct().order_by('user_id')
        return Response(list(ids))

    @action(detail=False, methods=['get'], url_path='prediction')
    def prediction(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        model_names = ['WeightedScoring', 'TrendAnalysis', 'CorrelationAnalysis', 'KMeansClustering']
        records = ClassificationResult.objects.filter(user_id=user_id).order_by('activity_date')

        dates = sorted(set(str(r.activity_date) for r in records))
        actual_map = {}
        predictions = {m: {} for m in model_names}

        for r in records:
            d = str(r.activity_date)
            actual_map[d] = r.actual_risk
            if r.model_name in predictions:
                predictions[r.model_name][d] = r.predicted_risk

        accuracy = {}
        for m in model_names:
            preds = [predictions[m].get(d) for d in dates]
            actuals = [actual_map.get(d) for d in dates]
            correct = sum(1 for a, p in zip(actuals, preds) if a == p and p is not None)
            total = sum(1 for p in preds if p is not None)
            accuracy[m] = round(correct / total, 4) if total > 0 else 0

        return Response({
            'dates': dates,
            'actual_risk': [actual_map.get(d) for d in dates],
            'predictions': {m: [predictions[m].get(d) for d in dates] for m in model_names},
            'accuracy': accuracy,
        })

    @action(detail=False, methods=['get'], url_path='prediction-users')
    def prediction_users(self, request):
        ids = (ClassificationResult.objects
               .values_list('user_id', flat=True).distinct().order_by('user_id'))
        return Response(list(ids))


class TrendAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TrendAnalysisSerializer

    def get_queryset(self):
        qs = TrendAnalysis.objects.all()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    @action(detail=False, methods=['get'], url_path='chart')
    def chart(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        records = TrendAnalysis.objects.filter(user_id=user_id).order_by('activity_date')
        return Response({
            'dates': [str(r.activity_date) for r in records],
            'stress_score': [float(r.stress_score) if r.stress_score else None for r in records],
            'score_7day_avg': [float(r.score_7day_avg) if r.score_7day_avg else None for r in records],
            'score_change_rate': [float(r.score_change_rate) if r.score_change_rate else None for r in records],
            'trend_label': [r.trend_label for r in records],
        })

    @action(detail=False, methods=['get'], url_path='forecast')
    def forecast(self, request):
        user_id = request.query_params.get('user_id')
        days = int(request.query_params.get('days', 7))
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        records = list(
            TrendAnalysis.objects.filter(user_id=user_id)
            .order_by('activity_date')
            .values_list('activity_date', 'stress_score')
        )
        if len(records) < 3:
            return Response({'error': 'insufficient data'}, status=status.HTTP_400_BAD_REQUEST)

        dates = [r[0] for r in records]
        scores = np.array([float(r[1]) for r in records])

        # --- Linear regression on recent window ---
        window = min(14, len(scores))
        recent = scores[-window:]
        x = np.arange(window, dtype=float)
        slope, intercept = np.polyfit(x, recent, 1)

        # --- EWMA of last few points ---
        alpha = 0.3
        ewma = recent[-1]
        for s in recent[-5:]:
            ewma = alpha * s + (1 - alpha) * ewma

        # --- Blend: 60% EWMA base + 40% linear trend ---
        forecast_scores = []
        for i in range(1, days + 1):
            lr_val = intercept + slope * (window - 1 + i)
            blended = 0.6 * ewma + 0.4 * lr_val
            ewma = alpha * blended + (1 - alpha) * ewma
            forecast_scores.append(round(max(0, min(100, blended)), 2))

        # --- Confidence band from historical residual std ---
        residuals = recent - (intercept + slope * x)
        std = float(np.std(residuals))
        upper = [round(min(100, s + 1.5 * std * (1 + 0.1 * i)), 2)
                 for i, s in enumerate(forecast_scores)]
        lower = [round(max(0, s - 1.5 * std * (1 + 0.1 * i)), 2)
                 for i, s in enumerate(forecast_scores)]

        # --- Risk levels ---
        def risk(s):
            if s >= 65: return '高风险'
            if s >= 40: return '中风险'
            return '低风险'

        last_date = dates[-1]
        forecast_dates = [str(last_date + timedelta(days=i)) for i in range(1, days + 1)]

        # --- Overall trend direction ---
        if slope > 1:
            direction = '上升'
        elif slope < -1:
            direction = '下降'
        else:
            direction = '平稳'

        return Response({
            'history': {
                'dates': [str(d) for d in dates],
                'scores': scores.tolist(),
            },
            'forecast': {
                'dates': forecast_dates,
                'scores': forecast_scores,
                'upper': upper,
                'lower': lower,
                'risk_levels': [risk(s) for s in forecast_scores],
            },
            'summary': {
                'direction': direction,
                'slope': round(float(slope), 4),
                'last_score': float(scores[-1]),
                'avg_forecast': round(float(np.mean(forecast_scores)), 2),
            }
        })


class CorrelationMatrixViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CorrelationMatrixSerializer
    queryset = CorrelationMatrix.objects.all()
    pagination_class = None

    @action(detail=False, methods=['get'], url_path='heatmap')
    def heatmap(self, request):
        records = CorrelationMatrix.objects.all()
        features = sorted(set(
            list(CorrelationMatrix.objects.values_list('feature_x', flat=True).distinct())
        ))
        data = [
            [r.feature_x, r.feature_y, float(r.corr_value) if r.corr_value else 0]
            for r in records
        ]
        return Response({'features': features, 'data': data})


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    pagination_class = None

    @action(detail=False, methods=['get'], url_path='cluster-summary')
    def cluster_summary(self, request):
        data = (UserProfile.objects.values('cluster_label')
                .annotate(
                    count=Count('user_id'),
                    avg_stress=Avg('avg_stress_score'),
                    avg_sleep=Avg('avg_sleep_efficiency'),
                    avg_active=Avg('avg_active_minutes'),
                    avg_hr=Avg('avg_resting_hr'),
                    avg_sedentary=Avg('avg_sedentary_ratio'),
                ))
        return Response(list(data))


class HourlyPatternViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = HourlyPatternSerializer
    queryset = HourlyPattern.objects.all()
    pagination_class = None

    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request):
        ids = HourlyPattern.objects.values_list('user_id', flat=True).distinct().order_by('user_id')
        return Response(list(ids))

    @action(detail=False, methods=['get'], url_path='chart')
    def chart(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)
        records = HourlyPattern.objects.filter(user_id=user_id).order_by('hour_of_day')
        return Response({
            'hours': [r.hour_of_day for r in records],
            'avg_steps': [float(r.avg_steps) if r.avg_steps else 0 for r in records],
            'avg_calories': [float(r.avg_calories) if r.avg_calories else 0 for r in records],
            'avg_intensity': [float(r.avg_intensity) if r.avg_intensity else 0 for r in records],
        })


class ModelComparisonViewSet(viewsets.ViewSet):

    @action(detail=False, methods=['get'], url_path='metrics')
    def metrics(self, request):
        model_names = ['WeightedScoring', 'TrendAnalysis', 'CorrelationAnalysis', 'KMeansClustering']
        result = {}
        for name in model_names:
            metrics = {}
            for m in ModelMetrics.objects.filter(model_name=name):
                metrics[m.metric_name] = float(m.metric_value) if m.metric_value else 0
            result[name] = metrics
        return Response(result)

    @action(detail=False, methods=['get'], url_path='learning-curve')
    def learning_curve(self, request):
        model_names = ['WeightedScoring', 'TrendAnalysis', 'CorrelationAnalysis', 'KMeansClustering']
        result = {}
        for name in model_names:
            records = LearningCurve.objects.filter(model_name=name).order_by('train_size')
            result[name] = {
                'train_size': [r.train_size for r in records],
                'train_score': [float(r.train_score) if r.train_score else 0 for r in records],
                'test_score': [float(r.test_score) if r.test_score else 0 for r in records],
            }
        return Response(result)

    @action(detail=False, methods=['get'], url_path='feature-importance')
    def feature_importance(self, request):
        result = {}
        for fi in FeatureImportance.objects.all().order_by('model_name', 'rank_order'):
            name = fi.model_name
            if name not in result:
                result[name] = []
            result[name].append({
                'feature': fi.feature_name,
                'importance': float(fi.importance) if fi.importance else 0,
                'rank': fi.rank_order,
            })
        return Response(result)

    @action(detail=False, methods=['get'], url_path='confusion-matrix')
    def confusion_matrix(self, request):
        model_names = ['WeightedScoring', 'TrendAnalysis',
                       'CorrelationAnalysis', 'KMeansClustering']
        risk_levels = sorted(set(
            ClassificationResult.objects
            .values_list('actual_risk', flat=True)
        ))

        result = {}
        for name in model_names:
            records = ClassificationResult.objects.filter(model_name=name)
            matrix = []
            for actual in risk_levels:
                row = []
                for pred in risk_levels:
                    row.append(records.filter(
                        actual_risk=actual, predicted_risk=pred).count())
                matrix.append(row)

            actual_dist = {}
            pred_dist = {}
            for lv in risk_levels:
                actual_dist[lv] = records.filter(actual_risk=lv).count()
                pred_dist[lv] = records.filter(predicted_risk=lv).count()

            result[name] = {
                'matrix': matrix,
                'actual_dist': actual_dist,
                'pred_dist': pred_dist,
            }

        return Response({'risk_levels': risk_levels, 'models': result})
