"""
File validators for secure file uploads
"""
import mimetypes
from django.core.exceptions import ValidationError


class FileValidator:
    """Validate uploaded files for type, size, and content"""
    
    ALLOWED_IMAGE_TYPES = {
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
    }
    
    ALLOWED_IMAGE_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.webp', '.gif'
    }
    
    ALLOWED_AUDIO_TYPES = {
        'audio/mpeg',
        'audio/mp4',
        'audio/wav',
        'audio/ogg',
        'audio/flac',
    }
    
    ALLOWED_AUDIO_EXTENSIONS = {
        '.mp3', '.m4a', '.wav', '.ogg', '.flac'
    }
    
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50MB

    @staticmethod
    def validate_image(file):
        """Validate image file"""
        if not file:
            raise ValidationError("No file provided")
        
        # Check size
        if file.size > FileValidator.MAX_IMAGE_SIZE:
            raise ValidationError(f"Image too large. Maximum size: 5MB, got {file.size / 1024 / 1024:.1f}MB")
        
        # Check MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.name)[0]
        if mime_type not in FileValidator.ALLOWED_IMAGE_TYPES:
            raise ValidationError(f"Invalid image type: {mime_type}. Allowed: JPEG, PNG, WebP, GIF")
        
        # Check extension
        import os
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in FileValidator.ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(f"Invalid file extension: {ext}")
        
        # Check file signature (magic bytes) for JPEG
        if mime_type == 'image/jpeg':
            file.seek(0)
            header = file.read(3)
            if header[:2] != b'\xff\xd8':  # JPEG magic bytes
                raise ValidationError("File is not a valid JPEG image")
            file.seek(0)
        
        # Check file signature for PNG
        elif mime_type == 'image/png':
            file.seek(0)
            header = file.read(8)
            if header != b'\x89PNG\r\n\x1a\n':  # PNG magic bytes
                raise ValidationError("File is not a valid PNG image")
            file.seek(0)
        
        return True

    @staticmethod
    def validate_audio(file):
        """Validate audio file"""
        if not file:
            raise ValidationError("No file provided")
        
        # Check size
        if file.size > FileValidator.MAX_AUDIO_SIZE:
            raise ValidationError(f"Audio file too large. Maximum size: 50MB, got {file.size / 1024 / 1024:.1f}MB")
        
        # Check MIME type
        mime_type = file.content_type or mimetypes.guess_type(file.name)[0]
        if mime_type not in FileValidator.ALLOWED_AUDIO_TYPES:
            raise ValidationError(f"Invalid audio type: {mime_type}. Allowed: MP3, WAV, OGG, FLAC, M4A")
        
        # Check extension
        import os
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in FileValidator.ALLOWED_AUDIO_EXTENSIONS:
            raise ValidationError(f"Invalid file extension: {ext}")
        
        return True
