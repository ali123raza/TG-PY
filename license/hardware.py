"""
Hardware fingerprint generation.
Combines CPU ID + Disk serial + MAC address → SHA256 → unique device ID.
"""
import hashlib
import platform
import socket
import subprocess
import uuid
import logging

logger = logging.getLogger(__name__)


def _get_cpu_id() -> str:
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                "wmic cpu get ProcessorId", shell=True,
                stderr=subprocess.DEVNULL).decode()
            return out.strip().split("\n")[-1].strip()
        elif platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "Serial" in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass
    return platform.processor() or "UNKNOWN_CPU"


def _get_disk_serial() -> str:
    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                "wmic diskdrive get SerialNumber", shell=True,
                stderr=subprocess.DEVNULL).decode()
            serial = out.strip().split("\n")[-1].strip()
            if serial and serial != "SerialNumber":
                return serial
        elif platform.system() == "Linux":
            out = subprocess.check_output(
                ["udevadm", "info", "--query=all", "--name=/dev/sda"],
                stderr=subprocess.DEVNULL).decode()
            for line in out.splitlines():
                if "ID_SERIAL=" in line:
                    return line.split("=")[1].strip()
    except Exception:
        pass
    return "UNKNOWN_DISK"


def _get_mac() -> str:
    try:
        mac = uuid.getnode()
        if mac != uuid.getnode():  # randomized MAC
            return "RANDOM_MAC"
        return ":".join(f"{(mac >> i) & 0xff:02x}" for i in range(40, -1, -8))
    except Exception:
        return "UNKNOWN_MAC"


def get_hardware_id() -> str:
    """
    Generate a stable hardware fingerprint for this machine.
    Returns a 64-char hex SHA256 string.
    """
    cpu    = _get_cpu_id()
    disk   = _get_disk_serial()
    mac    = _get_mac()
    host   = socket.gethostname()

    raw = f"{cpu}|{disk}|{mac}|{host}"
    logger.debug("Hardware raw: %s", raw)

    return hashlib.sha256(raw.encode()).hexdigest()


def get_platform_info() -> dict:
    return {
        "hostname": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()}",
        "machine":  platform.machine(),
    }
