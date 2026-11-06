"""Accès Gmail en LECTURE SEULE (repris de sandbox/gmail_test.ipynb).

Chemins et boîte attendue dans ~/.sos-job/.env (hors dépôt) :
GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH, GMAIL_USER.
Jeton expiré ou révoqué (invalid_grant) : supprimer token.json et relancer (reconsentement, lecture seule).
"""
from __future__ import annotations

import base64
import os
from pathlib import Path

READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"


class GmailError(RuntimeError):
    pass


def _env() -> tuple[Path, Path, str]:
    from dotenv import load_dotenv
    load_dotenv(Path.home() / ".sos-job" / ".env")
    try:
        return Path(os.environ["GMAIL_CREDENTIALS_PATH"]), Path(os.environ["GMAIL_TOKEN_PATH"]), os.environ["GMAIL_USER"]
    except KeyError as exc:
        raise GmailError(f"variable {exc} absente de ~/.sos-job/.env") from None


def get_service(interactive: bool = True):
    """Service Gmail en lecture seule. interactive=False : pas de navigateur de consentement, erreur à la place."""
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials_path, token_path, expected_user = _env()
    creds = Credentials.from_authorized_user_file(str(token_path), [READONLY_SCOPE]) if token_path.exists() else None
    if not creds or not creds.valid:
        try:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                raise RefreshError("aucun jeton utilisable")
        except RefreshError as exc:
            if not interactive:
                raise GmailError(f"jeton Gmail invalide ({exc}) : supprime {token_path} et relance alertes.py") from None
            creds = InstalledAppFlow.from_client_secrets_file(str(credentials_path), [READONLY_SCOPE]).run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    if set(creds.scopes or []) != {READONLY_SCOPE}:  # garde-fou : lecture seule uniquement
        raise GmailError(f"scopes refusés : {creds.scopes}. Supprime {token_path} et relance.")
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    address = service.users().getProfile(userId="me").execute()["emailAddress"]
    if address.lower() != expected_user.lower():
        raise GmailError(f"mauvaise boîte : {address}")
    return service


def search(service, query: str, limit: int = 50) -> list[str]:
    """IDs des messages correspondant à la requête Gmail (plus récents d'abord)."""
    ids, token = [], None
    while len(ids) < limit:
        resp = service.users().messages().list(userId="me", q=query, pageToken=token, maxResults=min(100, limit)).execute()
        ids += [m["id"] for m in resp.get("messages", [])]
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids[:limit]


def _find_part(payload: dict, mime: str) -> str | None:
    if payload.get("mimeType") == mime and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        found = _find_part(part, mime)
        if found:
            return found
    return None


def get_message(service, msg_id: str) -> dict:
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
    return {"id": msg["id"], "from": headers.get("from", ""), "subject": headers.get("subject", ""),
            "date_ms": int(msg["internalDate"]), "html": _find_part(msg["payload"], "text/html") or "",
            "text": _find_part(msg["payload"], "text/plain") or ""}
