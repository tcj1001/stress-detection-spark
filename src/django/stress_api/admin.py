from django.contrib import admin
from .models import DailyStress, TrendAnalysis, CorrelationMatrix, UserProfile, HourlyPattern

admin.site.register(DailyStress)
admin.site.register(TrendAnalysis)
admin.site.register(CorrelationMatrix)
admin.site.register(UserProfile)
admin.site.register(HourlyPattern)
