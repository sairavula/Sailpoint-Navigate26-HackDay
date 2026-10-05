#!/usr/bin/env python3
"""
Store the SailPoint demo-tenant PAT in the OS credential store
(macOS Keychain or Windows Credential Manager, via keyring).

Same keyring service/accounts the server reads:
  service: sailpoint-isc-hackday   accounts: client_id, client_secret

Values are typed at a hidden prompt (getpass), so they never land in
shell history, files, or the screen.

Windows, already vaulted by hand (Credential Manager UI or cmdkey)? keyring resolves
<service> first, then "<account>@<service>". Create two Generic Credentials:
  address: client_id@sailpoint-isc-hackday       user: client_id
  address: client_secret@sailpoint-isc-hackday   user: client_secret
then run --check to confirm the server can read them.

Demo-app key (needed for quarantine step 2, disabling the agent in its target app):
  service: saas-demo-api   account: api_key   (value starts with sck_)

Usage:
  python store_credentials.py                    # store / overwrite the PAT
  python store_credentials.py --target           # store / overwrite the demo-app key
  python store_credentials.py --check            # confirm all entries exist (prints no secrets)
  python store_credentials.py --delete           # remove all entries after Hack Day
"""

import getpass
import os
import sys

import keyring
from keyring.errors import PasswordDeleteError

SERVICE = os.getenv("HACKDAY_KEYCHAIN_SERVICE", "sailpoint-isc-hackday")
ACCOUNTS = ("client_id", "client_secret")
TARGET_SERVICE = os.getenv("TARGET_APP_KEY_SERVICE", "saas-demo-api")
TARGET_ACCOUNT = "api_key"


def check() -> int:
    backend = type(keyring.get_keyring()).__name__
    missing = [a for a in ACCOUNTS if not keyring.get_password(SERVICE, a)]
    print(f"backend={backend} service={SERVICE}")
    if missing:
        print(f"MISSING: {', '.join(missing)}")
        return 1
    print("OK: client_id and client_secret are stored")
    if keyring.get_password(TARGET_SERVICE, TARGET_ACCOUNT):
        print(f"OK: demo-app key stored (service={TARGET_SERVICE})")
    else:
        print(f"INFO: demo-app key not stored; quarantine will skip the target-app disable. Run: python store_credentials.py --target")
    return 0


def store() -> int:
    for account in ACCOUNTS:
        value = getpass.getpass(f"PAT {account}: ").strip()
        if len(value) < 10:
            print(f"ERROR: {account} looks too short; nothing stored for it.")
            return 1
        keyring.set_password(SERVICE, account, value)
    return check()


def store_target() -> int:
    value = getpass.getpass("Demo-app API key (sck_...): ").strip()
    if not value.startswith("sck_"):
        print("ERROR: demo-app keys start with sck_; nothing stored.")
        return 1
    keyring.set_password(TARGET_SERVICE, TARGET_ACCOUNT, value)
    print(f"OK: demo-app key stored (service={TARGET_SERVICE})")
    return 0


def delete() -> int:
    for service, account in [(SERVICE, a) for a in ACCOUNTS] + [(TARGET_SERVICE, TARGET_ACCOUNT)]:
        try:
            keyring.delete_password(service, account)
            print(f"deleted {service}/{account}")
        except PasswordDeleteError:
            print(f"not found: {service}/{account}")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check())
    if "--delete" in sys.argv:
        sys.exit(delete())
    if "--target" in sys.argv:
        sys.exit(store_target())
    sys.exit(store())
