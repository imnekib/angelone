# modules/exceptions.py

class AuthenticationError(Exception):
    """Exception raised for authentication failures."""
    pass

class TokenError(Exception):
    """Exception raised for token handling failures."""
    pass
