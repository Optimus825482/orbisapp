"""
Environment Configuration Management Module

This module provides secure environment variable handling with validation
and proper error messaging for missing required variables.
"""

import os
import sys
import logging
from typing import Optional, List
from pathlib import Path

from dotenv import load_dotenv
import os
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

logger = logging.getLogger(__name__)


class EnvironmentConfigError(Exception):
    """Raised when required environment variables are missing or invalid."""
    pass


class EnvConfig:
    """
    Secure environment configuration manager with validation.
    
    Ensures all sensitive configuration is loaded from environment variables
    with no hardcoded fallback values for production secrets.
    """
    
    # Required environment variables (no defaults allowed)
    REQUIRED_VARS: List[str] = [
        "OPENCAGE_API_KEY",
        "SECRET_KEY",  # Required for session security in production
        # Add other production-critical variables as needed
    ]
    
    # Optional variables with safe defaults
    OPTIONAL_VARS: dict = {
        "FLASK_ENV": "development",
        "FLASK_DEBUG": "False",
        "SESSION_COOKIE_SECURE": "auto",  # Auto: True in production, False in development
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "0",
        "REDIS_PASSWORD": "",  # Empty in development
    }
    
    # API Keys (must be set in production)
    API_KEYS: List[str] = [
        "OPENCAGE_API_KEY",
        "HYPERBOLIC_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
        "GEMINI_API_KEY",
    ]
    
    # Supabase Configuration
    SUPABASE_VARS: List[str] = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_SERVICE_KEY",
    ]
    
    @classmethod
    def validate_required(cls) -> None:
        """
        Validate that all required environment variables are set.
        
        Raises:
            EnvironmentConfigError: If any required variable is missing or empty.
        """
        missing_vars = []
        
        for var_name in cls.REQUIRED_VARS:
            value = os.getenv(var_name)
            if not value or value.strip() == "":
                missing_vars.append(var_name)
        
        if missing_vars:
            error_msg = (
                f"CRITICAL: Required environment variables are missing: {', '.join(missing_vars)}\n"
                f"Please set these variables in your .env file or environment.\n"
                f"See .env.example for reference."
            )
            logger.critical(error_msg)
            raise EnvironmentConfigError(error_msg)
    
    @classmethod
    def get_required(cls, var_name: str) -> str:
        """
        Get a required environment variable.
        
        Args:
            var_name: Name of the environment variable.
            
        Returns:
            The value of the environment variable.
            
        Raises:
            EnvironmentConfigError: If the variable is missing or empty.
        """
        value = os.getenv(var_name)
        if not value or value.strip() == "":
            raise EnvironmentConfigError(
                f"Required environment variable '{var_name}' is not set or empty."
            )
        return value.strip()
    
    @classmethod
    def get_optional(cls, var_name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get an optional environment variable with a default value.
        
        Args:
            var_name: Name of the environment variable.
            default: Default value if variable is not set.
            
        Returns:
            The value of the environment variable or the default.
        """
        value = os.getenv(var_name)
        if value is None:
            return default
        return value.strip() if value.strip() else default
    
    @classmethod
    def get_bool(cls, var_name: str, default: bool = False) -> bool:
        """
        Get a boolean environment variable.
        
        Args:
            var_name: Name of the environment variable.
            default: Default value if variable is not set.
            
        Returns:
            Boolean value of the environment variable.
        """
        value = os.getenv(var_name, "").lower()
        if value in ("true", "1", "yes", "on"):
            return True
        if value in ("false", "0", "no", "off"):
            return False
        return default
    
    @classmethod
    def get_int(cls, var_name: str, default: int = 0) -> int:
        """
        Get an integer environment variable.
        
        Args:
            var_name: Name of the environment variable.
            default: Default value if variable is not set or invalid.
            
        Returns:
            Integer value of the environment variable.
        """
        try:
            return int(os.getenv(var_name, str(default)))
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {var_name}, using default: {default}")
            return default
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if the application is running in production mode."""
        return os.getenv("FLASK_ENV", "development") == "production"
    
    @classmethod
    def get_session_cookie_secure(cls) -> bool:
        """
        Get SESSION_COOKIE_SECURE setting based on environment.
        
        Returns:
            True in production, False in development, or custom value from env.
        """
        value = cls.get_optional("SESSION_COOKIE_SECURE", "auto")
        if value == "auto":
            return cls.is_production()
        return cls.get_bool("SESSION_COOKIE_SECURE", cls.is_production())
    
    @classmethod
    def validate_api_keys(cls) -> None:
        """
        Validate that at least one AI API key is configured.
        
        Logs warnings if API keys are missing but doesn't raise an error
        as some features may work without specific APIs.
        """
        api_keys_available = []
        api_keys_missing = []
        
        for key_name in cls.API_KEYS:
            if os.getenv(key_name):
                api_keys_available.append(key_name)
            else:
                api_keys_missing.append(key_name)
        
        if api_keys_available:
            logger.info(f"Available API keys: {', '.join(api_keys_available)}")
        
        if api_keys_missing:
            logger.warning(f"Missing API keys: {', '.join(api_keys_missing)}")
    
    @classmethod
    def load_env_file(cls, env_path: Optional[str] = None) -> None:
        """
        Load environment variables from .env file.
        
        Args:
            env_path: Path to .env file. If None, searches in standard locations.
        """
        try:
            from dotenv import load_dotenv
            
            if env_path:
                load_dotenv(env_path)
            else:
                # Try to find .env in standard locations
                possible_paths = [
                    Path.cwd() / ".env",
                    Path(__file__).parent.parent / ".env",
                    Path(__file__).parent / ".env",
                ]
                
                for path in possible_paths:
                    if path.exists():
                        load_dotenv(path)
                        logger.info(f"Loaded environment variables from: {path}")
                        break
                else:
                    logger.warning("No .env file found in standard locations")
                    
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env file loading")
    
    @classmethod
    def initialize(cls) -> None:
        """
        Initialize environment configuration.
        
        This is the main entry point that should be called at application startup.
        It validates required variables and logs the configuration status.
        """
        # Load .env file if it exists
        cls.load_env_file()
        
        # Validate required variables
        try:
            cls.validate_required()
        except EnvironmentConfigError as e:
            logger.critical(str(e))
            if cls.is_production():
                # In production, fail fast if required vars are missing
                sys.exit(1)
            else:
                # In development, log but continue
                logger.warning("Running in development mode with missing required variables")
        
        # Validate API keys (warning only)
        cls.validate_api_keys()
        
        # Log environment mode
        mode = "production" if cls.is_production() else "development"
        logger.info(f"Application running in {mode} mode")
        logger.info(f"Session cookie secure: {cls.get_session_cookie_secure()}")


# Convenience functions
def get_env(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with optional default."""
    return EnvConfig.get_optional(var_name, default)


def get_env_required(var_name: str) -> str:
    """Get required environment variable, raises if missing."""
    return EnvConfig.get_required(var_name)


def is_production() -> bool:
    """Check if running in production mode."""
    return EnvConfig.is_production()


def is_secure_cookies() -> bool:
    """Get session cookie secure setting."""
    return EnvConfig.get_session_cookie_secure()
