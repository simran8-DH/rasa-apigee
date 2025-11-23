import requests
import json
import time
from requests.auth import HTTPBasicAuth
from actions.properties import (
    AUTH_URL, API_URL, USERNAME, PASSWORD,CLIENT_ID, ENCRYPTION, TOKEN_EXPIRY_SECONDS
)

_cached_token = None
_cached_token_time = None


def get_jwt_token(auth_url, username, password):
    """Fetch JWT token using Basic Auth."""
    response = requests.post(auth_url, auth=HTTPBasicAuth(username, password))
    response.raise_for_status()
    return response.json().get("token")


def get_cached_token():
    global _cached_token, _cached_token_time

    now = time.time()

    # If existing token not expired → reuse
    if _cached_token and _cached_token_time:
        if (now - _cached_token_time) < TOKEN_EXPIRY_SECONDS:
            print("Reusing cached token...")
            return _cached_token

    # Else fetch new
    print("Fetching NEW token...")
    new_token = get_jwt_token(AUTH_URL, USERNAME, PASSWORD)
    _cached_token = new_token
    _cached_token_time = now
    return new_token


def call_main_api(api_url, auth_token, payload):
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

    # Simply ignore ENCRYPTION flag for now
    print(f"ENCRYPTION FLAG = {ENCRYPTION} (ignored, sending plain JSON)")
    
    if(ENCRYPTION=="NO"):
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    else:
        return "cant encrypt"


# if __name__ == "__main__":
#     token = get_cached_token()
#     print("\nToken:", token)

#     print("\nCalling Main API...")
#     result = call_main_api(API_URL, token, payload)
#     print("API Response:", result)
