"""Closed string vocabularies for Spotify integration."""

from enum import StrEnum


class SpotifyEnvVar(StrEnum):
    CLIENT_ID = "SPOTIFY_CLIENT_ID"


class SpotifyGrantType(StrEnum):
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"


class SpotifyOAuthParam(StrEnum):
    ADDITIONAL_TYPES = "additional_types"
    CLIENT_ID = "client_id"
    CODE = "code"
    CODE_CHALLENGE = "code_challenge"
    CODE_CHALLENGE_METHOD = "code_challenge_method"
    CODE_VERIFIER = "code_verifier"
    ERROR = "error"
    GRANT_TYPE = "grant_type"
    REDIRECT_URI = "redirect_uri"
    REFRESH_TOKEN = "refresh_token"
    RESPONSE_TYPE = "response_type"
    SCOPE = "scope"
    STATE = "state"


class SpotifyTokenField(StrEnum):
    ACCESS_TOKEN = "access_token"
    EXPIRES_AT = "expires_at"
    EXPIRES_IN = "expires_in"
    REFRESH_TOKEN = "refresh_token"
