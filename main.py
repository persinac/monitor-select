import argparse
import json
import logging
import logging.config
import os
import re
import time
from enum import IntEnum

from monitorcontrol import get_monitors, Monitor

logging.config.fileConfig("log.ini")
logger = logging.getLogger("console")
logger.name = "monitor-select"
logger.setLevel(logging.INFO)

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


INPUT_SOURCE_NAMES = {
    0x00: "Off",
    0x01: "VGA-1",
    0x02: "VGA-2",
    0x03: "DVI-1",
    0x04: "DVI-2",
    0x05: "Composite-1",
    0x06: "Composite-2",
    0x07: "S-Video-1",
    0x08: "S-Video-2",
    0x09: "Tuner-1",
    0x0A: "Tuner-2",
    0x0B: "Tuner-3",
    0x0C: "Component-1",
    0x0D: "Component-2",
    0x0E: "Component-3",
    0x0F: "DP-1",
    0x10: "DP-2",
    0x11: "HDMI-1",
    0x12: "HDMI-2",
    0x1F: "USB-C",
}


class InputSource(IntEnum):
    HDMI1 = 0x11
    HDMI2 = 0x12
    DP1 = 0x0F
    DP2 = 0x10
    DVI1 = 0x03
    VGA1 = 0x01
    USBC = 0x1F
    # Add more if needed


INPUT_NAME_MAP = {v.value: k for k, v in InputSource.__members__.items()}
NAME_TO_VALUE = {k: v.value for k, v in InputSource.__members__.items()}


CONFIG_FILE = "config.json"


def get_input_name(value: int) -> str:
    """Retrieve the name of an input source from its value.

    :param value:
    :return:
    """
    return INPUT_SOURCE_NAMES.get(value, f"Unknown (0x{value:02x})")


def parse_vcp_capabilities(raw: str) -> dict:
    """Extract information from the raw VCP capabilities string.

    :param raw:
    :return:
    """
    info = {}
    # Extract basic fields
    for key in ["prot", "type", "model", "mccs_ver", "mswhql"]:
        match = re.search(rf"{key}\(([^)]+)\)", raw, re.IGNORECASE)
        if match:
            info[key] = match.group(1)

    # Parse input source options from VCP code 60
    match = re.search(r"60\(\s*([0-9A-Fa-f\s]+)\)", raw)
    if match:
        hex_values = match.group(1).split()
        input_sources = [int(val, 16) for val in hex_values]
        info["inputs_conv"] = input_sources
        info["inputs_raw"] = hex_values

    return info


def log_monitor_info(monitor: Monitor, idx: int):
    """Log information about a single monitor.

    :param monitor:
    :param idx:
    :return:
    """
    logger.info(f"Monitor #{idx + 1}")
    try:
        with monitor:
            log_current_input(monitor)
            log_input_capabilities(monitor)
    except Exception as e:
        logger.info(f"  Monitor #{idx+1} access error: {e}")


def log_current_input(monitor: Monitor):
    """Get the current input source of a monitor."""
    try:
        current = monitor.get_input_source()
        if isinstance(current, int):
            current_val = current
        else:
            current_val = current.value
        current_name = get_input_name(current_val)
        logger.info(f"  Current Input: {current_name} (0x{current_val:02x})")
    except Exception as e:
        logger.info(f"  Failed to get current input: {e}")


def log_input_capabilities(monitor: Monitor):
    """Get the input capabilities of a monitor."""
    logger.info("  Retrieving monitor input sources...")
    time.sleep(0.1)  # some readings take time
    vcp_caps: dict = monitor.get_vcp_capabilities()
    time.sleep(0.1)

    inputs = vcp_caps.get("inputs", [])
    input_names = []

    for input_source in inputs:
        enum_name = input_source.name
        hex_value = input_source.value
        display_name = get_input_name(hex_value)
        input_names.append(f"{enum_name} ({display_name}, 0x{hex_value:02x})")

    str_inputs = ", ".join(input_names)

    logger.info(f"\t - Model: {vcp_caps.get('model', 'Unknown')}")
    logger.info(f"\t - Available inputs: {str_inputs}")


def list_monitors():
    """List all monitors and their input sources."""
    monitors = get_monitors()
    if not monitors:
        logger.info("No DDC/CI monitors detected.")
        return

    logger.info(f"Found {len(monitors)} monitor(s):\n")

    for idx, monitor in enumerate(monitors):
        log_monitor_info(monitor, idx)


def set_monitor_inputs(assignments):
    monitors = get_monitors()
    if not monitors:
        logger.info("No monitors detected.")
        return

    for assignment in assignments:
        if "=" not in assignment:
            logger.info(f"Ignoring invalid assignment: {assignment}")
            continue
        index_str, input_name = assignment.split("=", 1)
        try:
            index = int(index_str) - 1
            source_val = NAME_TO_VALUE[input_name.upper()]
        except (ValueError, KeyError):
            logger.info(f"Invalid input source '{input_name}' or monitor index '{index_str}'")
            continue

        if index < 0 or index >= len(monitors):
            logger.info(f"Monitor index {index+1} out of range")
            continue

        monitor = monitors[index]
        try:
            with monitor:
                logger.info(f"Setting Monitor #{index + 1} to {input_name.upper()} (0x{source_val:02X})")
                monitor.set_input_source(source_val)
        except Exception as e:
            logger.info(f"  Failed to set Monitor #{index+1}: {e}")


def toggle_inputs():
    # Define your monitor config sets
    profiles = {"work": ["1=HDMI1", "2=HDMI1"], "personal": ["1=DP1", "2=DP1"]}

    # Load last state
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            state = json.load(f)
    else:
        state = {"current": "personal"}  # default state

    # Toggle
    new_profile = "work" if state["current"] == "personal" else "personal"
    print(f"Toggling to: {new_profile}")

    # Save new state
    with open(CONFIG_FILE, "w") as f:
        json.dump({"current": new_profile}, f)

    # Run the assignment
    set_monitor_inputs(profiles[new_profile])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Input Source Tool")
    parser.add_argument("--list", action="store_true", help="List monitors and available inputs")
    parser.add_argument("--set", nargs="+", help="Set monitor input, e.g., 1=HDMI1 2=DP1")
    parser.add_argument("--toggle", action="store_true", help="Toggle between work/personal monitor profiles")

    args = parser.parse_args()
    if args.list:
        list_monitors()
    elif args.set:
        set_monitor_inputs(args.set)
    elif args.toggle:
        toggle_inputs()
    else:
        parser.print_help()
