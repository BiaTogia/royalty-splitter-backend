from rest_framework import serializers
from backend.models import SIEM_Event, SeverityLevel


class SeverityLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeverityLevel
        fields = ['id', 'severity_name']


class SIEMEventSerializer(serializers.ModelSerializer):
    severity_name = serializers.CharField(source='severity.severity_name', read_only=True)

    class Meta:
        model = SIEM_Event
        fields = ['id', 'user', 'event_type', 'severity', 'severity_name', 'timestamp', 'description']
        read_only_fields = ['id', 'severity_name', 'timestamp']
