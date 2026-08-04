#!/usr/bin/env python3

import pathlib
import subprocess
import time

PATH_TO_REMCTRL_SCRIPTS = "/home/pid1beb/sit/scripts"
POWER_ON = PATH_TO_REMCTRL_SCRIPTS + "/" + "remctrl_poweron.sh"
POWER_OFF = PATH_TO_REMCTRL_SCRIPTS + "/" + "remctrl_poweroff.sh"


def idc_power_cycle():
    assert pathlib.Path.exists(pathlib.Path(POWER_ON)), f"{POWER_ON} script not found."
    assert pathlib.Path.exists(pathlib.Path(POWER_OFF)), f"{POWER_OFF} script not found."

    print("Powering off IDC")
    off = subprocess.run(["sh", POWER_OFF], capture_output=True, text=True)
    if off.returncode:
        print(off.stderr)
        raise RuntimeError
    time.sleep(2)
    print("Powering on IDC")
    on = subprocess.run(["sh", POWER_ON], capture_output=True, text=True)
    if on.returncode:
        print(on.stderr)
        raise RuntimeError
    time.sleep(20)
    return
