"""Trigger path: tell a running bar to scan, or start one if none is running."""
import os
import socket
import subprocess
import sys

from . import config


def send(command):
    """True if a running bar accepted the command."""
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(1)
    try:
        s.connect(config.ui_socket())
        s.sendall(command.encode() + b"\n")
        return True
    except OSError:
        return False
    finally:
        s.close()


def trigger():
    if send("scan"):
        return
    subprocess.Popen([sys.executable, "-m", "czgram", "--bar"], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
