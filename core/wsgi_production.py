"""
Production WSGI configuration for Smart Factory project
Optimized for high load and stability
"""

import os
import sys
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set production environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings_production')

# Import Django after setting the environment
from django.core.wsgi import get_wsgi_application

# Get the WSGI application
application = get_wsgi_application()

# Production optimizations
try:
    from whitenoise import WhiteNoise
    application = WhiteNoise(application, root=str(BASE_DIR / 'staticfiles'))
    application.add_files(str(BASE_DIR / 'static'), prefix='static/')
    application.add_files(str(BASE_DIR / 'media'), prefix='media/')
except ImportError:
    pass  # WhiteNoise not available 