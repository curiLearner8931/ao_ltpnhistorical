from SmartApi.smartConnect import SmartConnect
import os
import pyotp
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

def get_connection():
    api_key = os.getenv("API_KEY")
    client_code = os.getenv("CLIENT_ID")  # This is your Angel One client code
    mpin = os.getenv("MPIN")              # Use MPIN in place of password
    totp_secret = os.getenv("TOTP_SECRET")  # Base32 encoded secret for TOTP

    if not all([api_key, client_code, mpin, totp_secret]):
        raise ValueError("Missing env vars: API_KEY, CLIENT_ID, MPIN, or TOTP_SECRET")

    obj = SmartConnect(api_key=api_key)

    try:
        logging.info("Generating TOTP...")
        totp = pyotp.TOTP(totp_secret).now()

        logging.info("Creating session...")
        data = obj.generateSession(
            clientCode=client_code,
            password=mpin,
            totp=totp
        )

        auth_token = data['data']['jwtToken']
        refresh_token = data['data']['refreshToken']
        obj.setAccessToken(auth_token)

        # ✅ Attach the token for use in historical-data API
        obj.jwt_token = auth_token

        logging.info("Session established successfully.")
        return obj

    except Exception as e:
        logging.error(f"Angel One login failed: {e}")
        raise RuntimeError("Session generation failed") from e
