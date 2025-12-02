from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from backend.models import Split, Track
from api.serializers.track import SplitSerializer


class SplitViewSet(viewsets.ModelViewSet):
    """
    CRUD for Splits - Users can only create/modify splits on their own tracks
    - GET /api/splits/ - List splits for user's own tracks
    - POST /api/splits/ - Create split (only on own tracks)
    - GET /api/splits/{id}/ - Get split details
    - PUT /api/splits/{id}/ - Update split (only on own tracks)
    - DELETE /api/splits/{id}/ - Delete split (only on own tracks)
    """
    serializer_class = SplitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter to only show splits for user's own tracks"""
        user = self.request.user
        if user.is_staff:
            return Split.objects.all()
        return Split.objects.filter(track__owner=user)

    def perform_create(self, serializer):
        """Verify user owns the track before creating split"""
        track_id = self.request.data.get('track')
        try:
            track = Track.objects.get(id=track_id)
            if track.owner != self.request.user and not self.request.user.is_staff:
                raise PermissionError("You can only add splits to your own tracks")
        except Track.DoesNotExist:
            raise ValueError("Track not found")
        
        # Explicitly pass track to serializer.save()
        serializer.save(track=track)

    def perform_update(self, serializer):
        """Verify user owns the track before updating split"""
        split = self.get_object()
        if split.track.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionError("You can only modify splits on your own tracks")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Verify user owns the track before deleting split"""
        split = self.get_object()
        if split.track.owner != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only delete splits on your own tracks'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
