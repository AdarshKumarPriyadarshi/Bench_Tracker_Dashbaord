import argparse
import os
import pathlib

from config.constants import APP_NAME, DEFAULT_TMP_DIR, DEFAULT_DDU_FLASH_SCRIPT
from system.host_pc import HostPC


def setup_argument_parser(session_id: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.set_defaults(modules={})

    # General settings:
    parser.add_argument(
        "--config",
        help="JSON config file",
        required=False,
        type=lambda p: pathlib.Path(p).absolute(),
    )
    parser.add_argument(
        "--debug",
        help="debug mode without modifying flashed software",
        action="store_true",
    )
    parser.add_argument("--download", help="download only", required=False, action="store_true")
    parser.add_argument(
        "--interactive",
        help="mode that guides the user step by step",
        action="store_true",
        default=True,
    )
    parser.add_argument(
        "--non-interactive",
        help="disables interactive mode",
        action="store_true",
        default=False,
    )
    parser.add_argument("--verbose", help="increase output verbosity", action="store_true")

    output = parser.add_argument_group("output")
    # NOTE: Using the config dir is an abuse but this way it is ensured
    # that the log files are not gone after power-cycles!
    output.add_argument(
        "--logdir",
        dest="output_logdir",
        help="path for log files",
        required=False,
        type=lambda p: pathlib.Path(p).absolute(),
        default=pathlib.Path(f"{pathlib.Path(os.path.expanduser('~')) / '.config' / APP_NAME}").absolute(),
    )
    output.add_argument(
        "--localstorage",
        dest="output_localstorage",
        help="path for downloaded files",
        required=False,
        type=lambda p: pathlib.Path(p).absolute(),
        default=pathlib.Path(
            f"/var/tmp/img/{APP_NAME}" if HostPC.is_ds_pc() else f"{pathlib.Path(os.path.expanduser('~')) / 'Downloads' / APP_NAME}").absolute(),
    )
    output.add_argument(
        "--workspace",
        dest="output_workspace",
        help="path for temporary files",
        required=False,
        type=lambda p: pathlib.Path(p).absolute(),
        default=DEFAULT_TMP_DIR / session_id,
    )

    # [artifactory]
    artifactory = parser.add_argument_group("artifactory")
    artifactory.add_argument("--artifactory-uri", help="artifactory uri", required=False, type=str)
    artifactory.add_argument("--artifactory-user", help="artifactory user", required=False, type=str)
    artifactory.add_argument("--artifactory-password", help="artifactory password", required=False, type=str)

    # [ssh]
    idc = parser.add_argument_group("idc")
    idc.add_argument("--idc-ip", help="IP adress of IDC", required=False, type=str, default="10.121.1.50")
    idc.add_argument("--idc-port", help="Port number of IDC", required=False, type=int, default=22)

    # [modules]
    update = parser.add_argument_group("update")  # mutually_exclusive_group(required=False)
    update.add_argument("--update-ddu", help="update idc via ddu flashing", action="store_true", required=False)
    update.add_argument("--update-ndas", help="update ndas", action="store_true", required=False)
    update.add_argument("--update-rrdata", help="update ndas", action="store_true", required=False)
    update.add_argument("--update-adaptive", help="update adaptive", action="store_true", required=False)
    update.add_argument("--update-bundle", help="update DDU bundle", action="store_true", required=False)

    clear = parser.add_argument_group("clear")
    clear.add_argument("--clear-adaptive-persistency", help="clear '/var/lib/adaptive'", action="store_true",
                       required=False)
    clear.add_argument("--clear-ddu-persistency", help="pass -c option to ddu flash_script", action="store_true",
                       required=False)

    # [ndas]
    ndas = parser.add_argument_group("ndas")
    ndas.add_argument(
        "--ndas-source",
        help="local path or url of NDAS tar file",
        required=False,
        type=str,
    )

    # [rrdata]
    rrdata = parser.add_argument_group("rrdata")
    rrdata.add_argument(
        "--rrdata-source",
        help="local path or url of NDAS RR DATA tar file",
        required=False,
        type=str,
    )

    # [adaptive]
    adaptive = parser.add_argument_group("adaptive")
    adaptive.add_argument(
        "--adaptive-source",
        help="local path or url of ADAPTIVE tar file or directory",
        required=False,
        type=str,
    )
    adaptive.add_argument(
        "--adaptive-adaptive",
        help="local path or url of ADAPTIVE adaptive partition tar file",
        required=False,
        type=str,
    )
    adaptive.add_argument(
        "--adaptive-persistency",
        help="local path or url of ADAPTIVE persistency partition tar file",
        required=False,
        type=str,
    )
    adaptive.add_argument(
        "--adaptive-stub_libs",
        help="local path or url of ADAPTIVE stub_libs partition tar file",
        required=False,
        type=str,
    )

    # [ddu]
    ddu = parser.add_argument_group("ddu")
    ddu.add_argument(
        "--ddu-source",
        help="local path or url of DDU tar file",
        required=False,
        type=str,
    )
    ddu.add_argument(
        "--ddu-script",
        help="local path or url flash_ddu.sh",
        required=False,
        type=str,
        default=DEFAULT_DDU_FLASH_SCRIPT,
    )
    ddu.add_argument(
        "--ddu-aurix-port",
        help="port name of aurix serial tty connection to IDC",
        required=False,
        type=str,
    )

    # [bundle]
    bundle = parser.add_argument_group("bundle")
    bundle.add_argument(
        "--bundle-source",
        help="local path or url to DDU bundle",
        required=False,
        type=str,
    )

    return parser
