#!/usr/bin/env python3
"""
InstaAuto Session Generator
Run this on your LOCAL machine (not Render) to create a login session file.
Then upload the generated file to the project's sessions/ folder.

Usage:
    python scripts/generate_session.py
"""
import os
import sys
import pickle

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instagrapi import Client
from instagrapi.exceptions import ChallengeRequired

def main():
    username = input("Instagram username: ").strip()
    password = input("Instagram password: ").strip()

    cl = Client()
    cl.delay_range = [3, 8]
    cl.set_country_code(91)
    cl.set_locale("en_IN")
    cl.set_timezone_offset(19800)
    cl.set_country("IN")
    cl.set_continent("AS")

    try:
        cl.login(username, password)
        print("✅ Login successful!")
    except ChallengeRequired:
        print("🔐 OTP required! Check your phone/email.")
        code = input("Enter OTP code: ").strip()
        cl.challenge_resolve(code=code)
        print("✅ Challenge resolved!")

    session_dir = "sessions"
    os.makedirs(session_dir, exist_ok=True)
    session_path = os.path.join(session_dir, f"{username}.session")
    with open(session_path, "wb") as f:
        pickle.dump(cl, f)
    print(f"✅ Session file saved: {session_path}")
    print(f"\nAb is file ko GitHub pe push karo:")
    print(f"  1. `git add {session_path}`")
    print(f"  2. `git commit -m 'add session for {username}'`")
    print(f"  3. `git push`")
    print(f"\nRender redeploy karo — ab login nahi maangega!")

if __name__ == "__main__":
    main()
