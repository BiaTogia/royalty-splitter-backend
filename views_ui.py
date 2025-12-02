from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@require_http_methods(["GET"])
@permission_classes([AllowAny])
def track_gallery(request):
    """
    Display the track gallery page with upload form and audio player.
    No authentication required for viewing; auth is handled via API token in frontend.
    """
    return render(request, 'track_gallery.html')
