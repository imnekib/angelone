# modules/auth.py

import os
import json
import tempfile
import pyotp
from SmartApi.smartConnect import SmartConnect
import logging
from modules.exceptions import AuthenticationError, TokenError

def clean_token(token):
    """Remove 'Bearer ' prefix from the token if present."""
    bearer_prefix = "Bearer "
    if token.startswith(bearer_prefix):
        return token[len(bearer_prefix):]
    return token

def save_tokens(tokens, token_file="tokens.json"):
    """Save authentication tokens to a JSON file atomically."""
    try:
        with tempfile.NamedTemporaryFile('w', delete=False, dir='.') as tf:
            json.dump(tokens, tf)
            temp_name = tf.name
        os.replace(temp_name, token_file)
        logging.getLogger("trading_bot").info("Tokens saved successfully.")
    except Exception as e:
        logging.getLogger("trading_bot").error(f"Failed to save tokens: {e}")
        raise TokenError("Unable to save tokens.")

def load_tokens(token_file="tokens.json"):
    """Load authentication tokens from a JSON file."""
    try:
        with open(token_file, "r") as tf:
            tokens = json.load(tf)
        return tokens
    except FileNotFoundError:
        logging.getLogger("trading_bot").info(f"{token_file} not found.")
        return None
    except json.JSONDecodeError:
        logging.getLogger("trading_bot").error(f"{token_file} is corrupted.")
        return None

def initial_authentication(obj, client_id, pin, totp_secret):
    """Perform initial authentication to obtain tokens."""
    try:
        totp = pyotp.TOTP(totp_secret)
        otp = totp.now()
        logging.getLogger("trading_bot").info("Generated OTP successfully.")

        session_data = obj.generateSession(client_id, pin, otp)

        if session_data.get('status'):
            auth_token = clean_token(session_data['data']['jwtToken'])
            refresh_token = session_data['data']['refreshToken']

            tokens = {
                "jwtToken": auth_token,
                "refreshToken": refresh_token
            }
            save_tokens(tokens)
            return auth_token
        else:
            error_message = session_data.get('message', 'Unknown error during authentication.')
            logging.getLogger("trading_bot").error(f"Login failed: {error_message}")
            raise AuthenticationError(f"Login failed: {error_message}")
    except Exception as e:
        logging.getLogger("trading_bot").error(f"Login failed: {e}")
        raise AuthenticationError("Initial authentication failed.")

def generate_new_token(obj, refresh_token):
    """Generate a new authentication token using the refresh token."""
    try:
        session_data = obj.generateToken(refresh_token)
        if session_data.get('status'):
            auth_token = clean_token(session_data['data']['jwtToken'])
            new_refresh_token = session_data['data']['refreshToken']

            tokens = {
                "jwtToken": auth_token,
                "refreshToken": new_refresh_token
            }
            save_tokens(tokens)
            logging.getLogger("trading_bot").info("Token refreshed successfully.")
            return auth_token
        else:
            error_message = session_data.get('message', 'Unknown error during token refresh.')
            logging.getLogger("trading_bot").warning(f"Token generation failed: {error_message}")
            return initial_authentication(
                obj,
                client_id=os.getenv("client_id"),
                pin=os.getenv("pin"),
                totp_secret=os.getenv("totp_secret")
            )
    except Exception as e:
        logging.getLogger("trading_bot").error(f"Error generating new token: {e}")
        return initial_authentication(
            obj,
            client_id=os.getenv("client_id"),
            pin=os.getenv("pin"),
            totp_secret=os.getenv("totp_secret")
        )

def get_auth_token(obj, client_id, pin, totp_secret):
    """Retrieve a valid authentication token, refreshing or re-authenticating if necessary."""
    tokens = load_tokens()
    if not tokens:
        return initial_authentication(obj, client_id, pin, totp_secret)

    auth_token = tokens.get("jwtToken")
    refresh_token = tokens.get("refreshToken")

    if not auth_token or not refresh_token:
        logging.getLogger("trading_bot").info("Invalid tokens found, re-authenticating.")
        return initial_authentication(obj, client_id, pin, totp_secret)

    obj.setAccessToken(auth_token)
    try:
        profile = obj.getProfile(refresh_token)
        if profile and profile.get('status'):
            logging.getLogger("trading_bot").info("Access Token is valid.")
            return auth_token
        else:
            logging.getLogger("trading_bot").warning("Access Token invalid. Attempting to generate new token...")
            return generate_new_token(obj, refresh_token)
    except Exception as e:
        logging.getLogger("trading_bot").error(f"Failed to validate token: {e}")
        return generate_new_token(obj, refresh_token)
