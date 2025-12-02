from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from backend.models import Track, StreamData
from backend.royalty_service import distribute_royalty_for_track, distribute_royalty_from_streams
from django.utils import timezone
from api.serializers.track import TrackSerializer


class TrackPagination(PageNumberPagination):
    """Pagination for track listings"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class TrackViewSet(viewsets.ModelViewSet):
    """
    CRUD + list for Tracks
    Supports file upload (multipart/form-data) for track audio files.
    - GET /api/tracks/ - List all tracks (paginated, 10 per page)
    - GET /api/tracks/?page_size=20 - Customize page size
    - GET /api/tracks/?search=query - Search tracks by title or genre
    - GET /api/tracks/?genre=pop - Filter by genre
    - GET /api/tracks/?ordering=-release_date - Sort by release date
    - POST /api/tracks/ - Create track (auto-assigns to authenticated user)
    - GET /api/tracks/{id}/ - Get track details
    - PUT /api/tracks/{id}/ - Update track (owner only)
    - DELETE /api/tracks/{id}/ - Delete track (owner only)
    - POST /api/tracks/{id}/distribute_royalties/ - Manually trigger royalty distribution
    """
    serializer_class = TrackSerializer
    permission_classes = [permissions.IsAuthenticated]
    from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = TrackPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['genre', 'owner']
    search_fields = ['title', 'genre']
    ordering_fields = ['release_date', 'title', 'duration']
    ordering = ['-release_date']

    def get_queryset(self):
        """
        Users see only their own tracks by default.
        Staff can see all tracks.
        """
        if self.request.user.is_staff:
            return Track.objects.all().select_related('owner').prefetch_related('splits', 'streams', 'royalties')
        else:
            return Track.objects.filter(owner=self.request.user).select_related('owner').prefetch_related('splits', 'streams', 'royalties')

    def perform_create(self, serializer):
        # Set owner to the currently authenticated user
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """Verify user owns the track before updating"""
        track = self.get_object()
        if track.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionError("You can only update your own tracks")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """Verify user owns the track before deleting"""
        track = self.get_object()
        if track.owner != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only delete your own tracks'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def distribute_royalties(self, request, pk=None):
        """
        Manually trigger royalty distribution for this track.
        This creates payouts for all collaborators based on their split percentages.
        
        POST /api/tracks/{id}/distribute_royalties/
        Response: {royalty_id, track_id, total_earning, payouts_count}
        """
        track = self.get_object()
        
        # Verify user is owner or staff
        if track.owner != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only distribute royalties for your own tracks'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if track has splits
        if not track.splits.exists():
            return Response(
                {'error': 'Track must have at least one split to distribute royalties'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            result = distribute_royalty_for_track(track)
            return Response({
                'success': True,
                'message': f'Royalties distributed successfully. {result["payouts_count"]} payouts created.',
                'royalty_id': result['royalty_id'],
                'track_id': result['track_id'],
                'total_earning': str(result['total_earning']),
                'payouts_count': result['payouts_count']
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to distribute royalties: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request, *args, **kwargs):
        # Handle multipart form where `splits` may be sent as a JSON string
        # Don't use .copy() on QueryDict with file uploads (causes pickle error)
        data = {}
        for key in request.data:
            if key == 'splits':
                # Handle splits as JSON string
                splits = request.data.get('splits')
                if isinstance(splits, str):
                    import json
                    try:
                        data['splits'] = json.loads(splits)
                    except Exception:
                        data['splits'] = []
                else:
                    data['splits'] = splits
            elif key != 'file':
                # Copy regular form fields
                data[key] = request.data.get(key)
        
        # Handle file separately to avoid pickling issues
        if 'file' in request.data:
            data['file'] = request.data['file']

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_streams_and_distribute(self, request, pk=None):
        """
        Increment streams for a track and distribute earnings for the new streams.

        Request body options:
        - add_streams: integer (number of streams to add). If provided, a StreamData row will be created.
        - platform: optional string (platform name)

        Only the track owner or staff may call this.
        """
        track = self.get_object()
        user = request.user
        if track.owner != user and not user.is_staff:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        add_streams = request.data.get('add_streams')
        platform = request.data.get('platform', 'manual')

        if add_streams is not None:
            try:
                add_streams = int(add_streams)
                if add_streams <= 0:
                    raise ValueError
            except Exception:
                return Response({'error': 'Invalid add_streams value'}, status=status.HTTP_400_BAD_REQUEST)

            # Create a StreamData record for the increment
            StreamData.objects.create(track=track, platform=platform, stream_count=add_streams, date_recorded=timezone.now().date())

        try:
            result = distribute_royalty_from_streams(track)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
