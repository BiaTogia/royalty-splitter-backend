"""
Input sanitization utilities for XSS prevention
"""
from django.utils.html import escape
from django.utils.text import slugify
import bleach


class InputSanitizer:
    """Sanitize user inputs to prevent XSS attacks"""
    
    ALLOWED_TAGS = []  # No HTML tags allowed for user inputs
    ALLOWED_ATTRIBUTES = {}
    
    @staticmethod
    def sanitize_text(text, max_length=None):
        """Sanitize plain text input"""
        if not text:
            return text
        
        # Escape HTML
        clean_text = escape(str(text).strip())
        
        # Truncate if needed
        if max_length and len(clean_text) > max_length:
            clean_text = clean_text[:max_length]
        
        return clean_text
    
    @staticmethod
    def sanitize_email(email):
        """Sanitize email input"""
        if not email:
            return email
        
        email = str(email).strip().lower()
        # Only alphanumeric, dots, dashes, underscores, and @
        import re
        if not re.match(r'^[a-z0-9._%-]+@[a-z0-9.-]+\.[a-z]{2,}$', email):
            raise ValueError("Invalid email format")
        
        return email
    
    @staticmethod
    def sanitize_slug(text):
        """Sanitize to URL-safe slug"""
        return slugify(text)
    
    @staticmethod
    def sanitize_filename(filename):
        """Sanitize filename to prevent path traversal and injection"""
        import os
        import re
        
        if not filename:
            return filename
        
        # Get filename without path
        filename = os.path.basename(filename)
        
        # Remove potentially dangerous characters
        # Keep only alphanumeric, dots, dashes, underscores
        safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
        
        # Limit length
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:250 - len(ext)] + ext
        
        return safe_name
