import os
from pathlib import Path
from env_config import EnvConfig, get_env_required, get_env

class Config:
    """
    Flask Configuration - Database stripped for client-side purely state.
    """
    # Secret Key - Required for session and flash messages
    SECRET_KEY = get_env("SECRET_KEY", os.urandom(24).hex())
    
    # API Keys
    OPENCAGE_API_KEY = get_env_required("OPENCAGE_API_KEY")
    DEEPSEEK_API_KEY = get_env("DEEPSEEK_API_KEY", "")
    GOOGLE_API_KEY = get_env("GOOGLE_API_KEY", "")
    OPENROUTER_API_KEY = get_env("OPENROUTER_API_KEY", "")

    # Session Configuration - Secure session management
    SESSION_TYPE = None  # Default Flask cookie session
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = 3600 * 24 * 7  # 1 week
    SESSION_USE_SIGNER = True  # Enable session signing for security
    SESSION_COOKIE_SECURE = EnvConfig.get_session_cookie_secure()
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "astro_session"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Feature Flags
    ENABLE_AI_INTERPRETATIONS = True
    ENABLE_TTS = True

    @staticmethod
    def init_app(app):
        EnvConfig.initialize()
        import logging
        log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
        app.logger.setLevel(log_level)

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    def __init__(self):
        # SECRET_KEY production'da zorunlu
        secret_key = os.getenv("SECRET_KEY")
        if not secret_key or secret_key == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY environment variable must be set in production! "
                "Generate a secure key with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
        EnvConfig.validate_required()

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}

def get_config(env_name=None):
    if env_name is None:
        env_name = os.getenv("FLASK_ENV", "development")
    return config.get(env_name, DevelopmentConfig)
