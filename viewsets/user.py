from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from backend.models import UserAccount
from api.serializers.user import UserAccountSerializer, UserRegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    User registration (public) and user management (authenticated, owner-only)
    - POST /api/users/ - Register new user (no auth required)
    - GET /api/users/me/ - Get current user details (auth required)
    - GET /api/users/{id}/ - Get any user details (auth required, but limited info for non-owners)
    - PUT /api/users/me/ - Update current user (auth required)
    - DELETE /api/users/me/ - Delete current user (auth required)
    """
    serializer_class = UserAccountSerializer

    def get_permissions(self):
        """Allow anonymous access for user registration, authenticated for other actions"""
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """Users can only see themselves; admins can see all"""
        user = self.request.user
        if user.is_staff:
            return UserAccount.objects.all()
        return UserAccount.objects.filter(id=user.id)

    def get_serializer_class(self):
        """Use registration serializer for create, regular serializer for other actions"""
        if self.action == 'create':
            return UserRegisterSerializer
        return UserAccountSerializer

    @action(detail=False, methods=['get', 'put', 'delete'])
    def me(self, request):
        """
        Get, update, or delete current user profile
        - GET /api/users/me/ - Get your profile
        - PUT /api/users/me/ - Update your profile
        - DELETE /api/users/me/ - Delete your account
        """
        user = request.user
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = self.get_serializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        elif request.method == 'DELETE':
            user.delete()
            return Response({'detail': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, *args, **kwargs):
        """Override to prevent users from deleting other accounts"""
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You can only delete your own account'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """List users with optional search by email"""
        search_query = request.query_params.get('search', '').strip()
        
        queryset = self.get_queryset()
        
        # If search query provided, filter by email
        if search_query:
            queryset = queryset.filter(email__icontains=search_query)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
