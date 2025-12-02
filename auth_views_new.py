from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import login as django_login
from django.middleware.csrf import get_token as get_csrf_token
from django.conf import settings
from backend.models import UserAccount
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from api.serializers.user import UserRegisterSerializer


@extend_schema(
    summary="Get Authentication Token",
    description="""
    Authenticate using email and password to receive an authentication token.
    Use this token in all subsequent API requests via the Authorization header.
    
    Format: Authorization: Token YOUR_TOKEN_HERE
    """,
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'example': 'user@example.com'},
                'password': {'type': 'string', 'example': 'password123'}
            },
            'required': ['email', 'password']
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'token': {'type': 'string', 'description': 'Authentication token'},
                'user_id': {'type': 'integer', 'description': 'User ID'},
                'email': {'type': 'string', 'description': 'User email'}
            }
        },
        401: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    tags=['Authentication'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def get_auth_token(request):
    """
    Get authentication token using email and password.
    
    POST body: {"email": "user@example.com", "password": "password123"}
    
    Returns: {"token": "xyz123", "user_id": 1, "email": "user@example.com"}
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {'error': 'email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        user = UserAccount.objects.get(email=email)
        if user.check_password(password):
            django_login(request, user)
            csrf_token = get_csrf_token(request)
            resp = Response({'user_id': user.id, 'email': user.email, 'detail': 'authenticated'})
            resp.set_cookie(settings.CSRF_COOKIE_NAME if hasattr(settings, 'CSRF_COOKIE_NAME') else 'csrftoken', csrf_token, httponly=False, secure=not settings.DEBUG, samesite='Lax')
            return resp
        else:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    except UserAccount.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@extend_schema(
    summary="Register New User",
    description="""
    Register a new user account and receive an authentication token.
    Use the returned token in all subsequent API requests via the Authorization header.
    
    Password must be at least 8 characters.
    """,
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'email': {'type': 'string', 'example': 'user@example.com'},
                'password': {'type': 'string', 'example': 'password123456'},
                'name': {'type': 'string', 'example': 'John Doe'},
                'country': {'type': 'string', 'example': 'USA'}
            },
            'required': ['email', 'password', 'name']
        }
    },
    responses={
        201: {
            'type': 'object',
            'properties': {
                'token': {'type': 'string', 'description': 'Authentication token'},
                'user_id': {'type': 'integer', 'description': 'User ID'},
                'email': {'type': 'string', 'description': 'User email'},
                'name': {'type': 'string', 'description': 'User name'}
            }
        },
        400: {'type': 'object', 'properties': {'error': {'type': 'string'}}}
    },
    tags=['Authentication'],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    Register a new user and get authentication token.
    
    POST body: {
        "email": "user@example.com",
        "password": "password123456",
        "name": "John Doe",
        "country": "USA"  // optional
    }
    
    Returns: {"token": "xyz123", "user_id": 1, "email": "user@example.com", "name": "John Doe"}
    """
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        django_login(request, user)
        csrf_token = get_csrf_token(request)
        resp = Response({'user_id': user.id, 'email': user.email, 'name': user.name, 'detail': 'registered'}, status=status.HTTP_201_CREATED)
        resp.set_cookie(settings.CSRF_COOKIE_NAME if hasattr(settings, 'CSRF_COOKIE_NAME') else 'csrftoken', csrf_token, httponly=False, secure=not settings.DEBUG, samesite='Lax')
        return resp
    else:
        return Response(
            {'error': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
