"""
M.A.R.K.E.T AI - Dynamic Port Reservation & Isolated Session Engine
Finds free network ports and manages isolated employee workspaces.
"""

import socket
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a TCP port is currently open and bound on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            # If connect succeeds, something is listening
            result = s.connect_ex((host, port))
            if result == 0:
                return True
        except Exception:
            pass

    # Also test if we can bind to it
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except Exception:
            return True


def find_free_port(start_port: int = 8100, end_port: int = 8200, reserved_ports: Optional[List[int]] = None) -> Optional[int]:
    """Scan port range and return first available free port."""
    reserved = set(reserved_ports or [])
    for port in range(start_port, end_port + 1):
        if port in reserved:
            continue
        if not is_port_in_use(port):
            return port
    return None


def get_available_ports_list(start_port: int = 8100, end_port: int = 8200, limit: int = 8, reserved_ports: Optional[List[int]] = None) -> List[int]:
    """Return a list of upcoming free ports."""
    reserved = set(reserved_ports or [])
    free_ports = []
    for port in range(start_port, end_port + 1):
        if port in reserved:
            continue
        if not is_port_in_use(port):
            free_ports.append(port)
            if len(free_ports) >= limit:
                break
    return free_ports
