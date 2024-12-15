import logging
from settings.config import settings 

logging.info(f"Initializing EmailService with SMTP Server: {settings.smtp_server}, Port: {settings.smtp_port}")
