from rest_framework import viewsets, permissions
from backend.models import SIEM_Event, SeverityLevel
from api.serializers.siem import SIEMEventSerializer, SeverityLevelSerializer


class SIEMEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only SIEM event access (admin only)
    - GET /api/siem-events/ - List security events (admin only)
    - GET /api/siem-events/{id}/ - Get event details (admin only)
    """
    queryset = SIEM_Event.objects.all()
    serializer_class = SIEMEventSerializer
    permission_classes = [permissions.IsAdminUser]


class SeverityLevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only severity levels (admin can create/modify via admin panel)
    - GET /api/severity-levels/ - List severity levels
    - GET /api/severity-levels/{id}/ - Get level details
    
    Severity levels are system-managed and can only be modified by admins via admin panel.
    """
    queryset = SeverityLevel.objects.all()
    serializer_class = SeverityLevelSerializer
    permission_classes = [permissions.IsAdminUser]
