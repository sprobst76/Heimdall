"""Interactive device registration for the Heimdall agent.

Walks the user through:
1. Connecting to the Heimdall server
2. Logging in with parent credentials
3. Selecting the child to assign this device to
4. Registering the device and storing the token locally
"""

from __future__ import annotations

import getpass
import platform
import socket
import sys
from pathlib import Path

import httpx

from .config import AgentConfig

_API_PREFIX = "/api/v1"


def _get_machine_id() -> str:
    """Return a stable, unique identifier for this machine."""
    if sys.platform == "win32":
        try:
            import winreg  # type: ignore[import-untyped]

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            return str(value)
        except Exception:
            pass

    # Linux / macOS fallback
    machine_id_path = Path("/etc/machine-id")
    if machine_id_path.exists():
        return machine_id_path.read_text().strip()

    # Last resort: hostname + platform
    return f"{socket.gethostname()}-{platform.machine()}"


def register_interactive() -> None:
    """Run the interactive registration flow."""
    print()
    print("=== Heimdall Agent — Geraeteregistrierung ===")
    print()

    # Step 1: Server URL
    default_url = "http://localhost:8000"
    server_url = input(f"  Server-URL [{default_url}]: ").strip() or default_url

    api_base = f"{server_url}{_API_PREFIX}"

    # Step 2: Login
    print()
    email = input("  Eltern-E-Mail: ").strip()
    password = getpass.getpass("  Passwort: ")

    if not email or not password:
        print("  Fehler: E-Mail und Passwort sind erforderlich.")
        sys.exit(1)

    with httpx.Client(base_url=api_base, timeout=30.0) as client:
        # Authenticate
        print()
        print("  Anmeldung ...")
        try:
            resp = client.post("/auth/login", json={"email": email, "password": password})
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            print(f"  Fehler: Login fehlgeschlagen — {detail or e.response.status_code}")
            sys.exit(1)
        except httpx.ConnectError:
            print(f"  Fehler: Server nicht erreichbar unter {server_url}")
            sys.exit(1)

        tokens = resp.json()
        access_token = tokens["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # Step 3: Get user info to find family_id
        resp = client.get("/auth/me", headers=auth_headers)
        resp.raise_for_status()
        me = resp.json()
        family_id = me["family_id"]
        print(f"  Angemeldet als: {me['name']} (Familie: {family_id[:8]}...)")

        # Step 4: List children in the family
        resp = client.get(f"/families/{family_id}/members", headers=auth_headers)
        resp.raise_for_status()
        members = resp.json()
        children = [m for m in members if m["role"] == "child"]

        if not children:
            print("  Fehler: Keine Kinder in dieser Familie gefunden.")
            print("  Bitte zuerst ein Kind im Eltern-Portal anlegen.")
            sys.exit(1)

        print()
        print("  Kinder:")
        for i, child in enumerate(children, 1):
            age_str = f", {child['age']} Jahre" if child.get("age") else ""
            print(f"    [{i}] {child['name']}{age_str}")

        # Select child
        print()
        while True:
            choice = input(f"  Kind auswaehlen [1-{len(children)}]: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(children):
                    selected_child = children[idx]
                    break
            except ValueError:
                pass
            print(f"    Bitte eine Zahl von 1 bis {len(children)} eingeben.")

        child_id = selected_child["id"]
        print(f"  Ausgewaehlt: {selected_child['name']}")

        # Step 5: Device name
        default_name = f"{selected_child['name']}-PC"
        device_name = input(f"  Geraetename [{default_name}]: ").strip() or default_name

        # Step 6: Register device
        machine_id = _get_machine_id()
        print()
        print(f"  Registriere Geraet '{device_name}' ...")

        try:
            resp = client.post(
                f"/children/{child_id}/devices/",
                json={
                    "name": device_name,
                    "type": "windows",
                    "device_identifier": machine_id,
                },
                headers=auth_headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            detail = ""
            try:
                detail = e.response.json().get("detail", "")
            except Exception:
                pass
            print(f"  Fehler: Registrierung fehlgeschlagen — {detail or e.response.status_code}")
            sys.exit(1)

        result = resp.json()
        device_token = result["device_token"]
        device_info = result["device"]
        device_id = device_info["id"]

    # Step 7: Save config
    config = AgentConfig(
        server_url=server_url,
        device_token=device_token,
        device_id=device_id,
        child_id=child_id,
        device_name=device_name,
    )
    config.save()

    print()
    print("  Registrierung erfolgreich!")
    print(f"  Device-ID: {device_id}")
    print(f"  Kind:      {selected_child['name']}")
    print(f"  Token:     {device_token[:8]}... (gespeichert)")
    print()
    print("  Starte den Agent mit: heimdall-agent")
    print()
