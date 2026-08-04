#!/usr/bin/env python3

import logging
import pathlib
import shutil
import sys

from config.commandline_args import setup_argument_parser
from config.commandline_ui import CommandlineUI
from config.config_front_loader import ConfigFrontLoader
from config.constants import APP_NAME, DEFAULT_TMP_DIR
from config.flash_config import FlashConfig
from flashing.flash_graph_creator import FlashGraphCreator
from log.file_and_stream_logger import FileAndStreamLogger
from log.format import Style, FGColor
from log.utils import dump_dict_as_table, dump_figlet_digital_txt, get_current_datetime_string_literal, \
    dump_colored_figlet_txt
from utils.file_system import dir_empty


def main(args: FlashConfig, session_id: str) -> int:
    """Covers the main use-case of drburn.

    Args:
        args (_type_): _description_

    Raises:
        FileNotFoundError: _description_
        FileExistsError: _description_
        FileExistsError: _description_
    """
    # [LOGGING]
    logdir = args.output.logdir
    assert logdir is not None
    assert isinstance(
        logdir, pathlib.Path
    ), f"Logging directory is expected to be an instance of pathlib.Path, but it is {type(logdir)}"
    if not logdir.exists():
        try:
            logdir.mkdir(parents=True, exist_ok=True)
        except:
            print(f"Failed to create logging directory {logdir}")
            print(f"Aborting...")
            return 1
    if not logdir.is_dir():
        print(f"Logging directory {logdir} is not a directory")
        return 1

    # Use session_id for logging, thus all logs/dumps from this run have the same date-time-literal.
    app_logger = FileAndStreamLogger(logdir=logdir, name=f"{APP_NAME}-{session_id}", debug=args.debug)
    app_logger.debug(f"Exec command: {' '.join(sys.argv)}")
    app_logger.info(dump_colored_figlet_txt("  Dr. Burn  ", fgcolor="\033[38;5;236m", bgcolor="\033[48;5;199m"))
    app_logger.info(f"Application name: {APP_NAME}")

    # [CONFIGURATION]
    config = FlashConfig.from_config(args, logger=app_logger)
    if config is None:
        app_logger.error(f"Failed to read configuration.")
        app_logger.error(f"Aborting...")
        return 1

    # [LOGGING LEVEL FROM CONFIG]
    if config.debug:
        app_logger.debug("Setting log level DEBUG for streamlogging.")
        app_logger.setConsoleLogLevel(logging.DEBUG)

    # [OUTPUT]
    # workspace
    workspace = config.output.workspace
    assert workspace is not None
    assert isinstance(
        workspace, pathlib.Path
    ), f"Workspace is expected to be an instance of pathlib.Path, but it is {type(workspace)}"
    # Clear default workspace parent i.e. /tmp/drburn
    shutil.rmtree(DEFAULT_TMP_DIR, ignore_errors=True)
    if workspace.is_dir() and not dir_empty(workspace):
        app_logger.error(f"Workspace {workspace} already exists and is not an empty directory")
        app_logger.error(f"Aborting...")
        return 1
    if not workspace.exists():
        try:
            workspace.mkdir(parents=True, exist_ok=True)
        except:
            app_logger.error(f"Failed to create workspace {workspace}")
            app_logger.error(f"Aborting...")
            return 1
    if not workspace.is_dir():
        app_logger.error(f"Workspace {workspace} is not a directory")
        app_logger.error(f"Aborting...")
        return 1

    # localstorage
    localstorage = config.output.localstorage
    assert localstorage is not None
    assert isinstance(
        localstorage, pathlib.Path
    ), f"Local storage is expected to be an instance of pathlib.Path, but it is {type(localstorage)}"
    if not localstorage.exists():
        try:
            localstorage.mkdir(parents=True, exist_ok=True)
        except:
            app_logger.error(f"Failed to create local storage {localstorage}")
            app_logger.error(f"Aborting...")
            return 1
    if not localstorage.is_dir():
        app_logger.error(f"Local storage {localstorage} is not a directory")
        app_logger.error(f"Aborting...")
        return 1

    # ==============================================
    # I. CREATE
    # #  - User interaction
    # #  - Front loader
    # ==============================================
    flashUI = CommandlineUI(logger=app_logger)
    frontLoader = ConfigFrontLoader(logger=app_logger)

    # ==============================================
    # II. Preparations for FLASHING:
    #  a) interact with user
    #  b) perform front loading of (payload) data
    # ==============================================

    # a)
    user_config = flashUI.run(config)
    app_logger.debug(f"Config after CommandlineUI\n{dump_dict_as_table(user_config.dict())}")

    # b)
    app_logger.info(dump_figlet_digital_txt("FrontLoader"))
    flash_config, flash_config_with_errors = frontLoader.run(user_config)
    app_logger.debug(f"Config after ConfigFrontLoader\n{dump_dict_as_table(flash_config_with_errors.dict())}")

    # if flash_config == flash_config_with_errors:
    #     print("Equal flash_configs !!")

    if not flash_config == flash_config_with_errors:
        app_logger.error("Failed to resolve some URLs to local paths.")
        corrected_user_config = flashUI.run(flash_config_with_errors)
        app_logger.debug(f"Corrected config after CommandlineUI\n{dump_dict_as_table(corrected_user_config.dict())}")
        if corrected_user_config != flash_config_with_errors:
            flash_config, flash_config_with_errors = frontLoader.run(corrected_user_config)
            app_logger.debug(
                f"Corrected config after ConfigFrontLoader\n{dump_dict_as_table(flash_config_with_errors.dict())}"
            )
        if not flash_config == flash_config_with_errors:
            app_logger.error("Aborting...")
            return 1

    # ==============================================
    # III. [FLASHING]
    # ==============================================
    flash_success = False
    if not flash_config.download:
        creator = FlashGraphCreator(logger=app_logger)
        flasher = creator.createFlashGraph(flash_config)
        if not flasher:
            sys.exit(1)
        flash_success = flasher.run()
        flasher.print_summary()
    if flash_success:
        # Clear download dir on success
        shutil.rmtree(localstorage, ignore_errors=True)

        # Auto-update dashboard with new SW version and architecture
        try:
            import re, socket, json as _json
            from urllib.request import Request, urlopen
            for _handler in logging.getLogger(f"{APP_NAME}-{session_id}").handlers:
                _handler.flush()
            _url = None
            _log_path = str(app_logger.filename)
            with open(_log_path, "r") as _f:
                for _line in _f:
                    if "Processing URL" in _line and "artifacts.swf" in _line:
                        _url_match = re.search(r'(https://artifacts\.swf[^\s]+)', _line)
                        if _url_match:
                            _url = _url_match.group(1)
            if _url:
                _sw = re.search(r'/R(\d+\.\d+\.\d+)/', _url)
                _arch = re.search(r'Base_(st\d+)', _url, re.IGNORECASE)
                if _sw and _arch:
                    _hostname_map = {
                        "c623lrd90775115": 1, "c623lrd89895681": 2,
                        "c623lrd84052272": 3, "c623lrd83422370": 4,
                        "c623lrd90042984": 5,
                    }
                    _bench_id = _hostname_map.get(socket.gethostname().lower())
                    if _bench_id:
                        _payload = _json.dumps({
                            "bench_id": _bench_id,
                            "sw_version": "R" + _sw.group(1),
                            "architecture": _arch.group(1).upper()
                        }).encode("utf-8")
                        _req = Request(
                            "http://c623drd41380439:8000/api/update-bench-sw",
                            data=_payload,
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        urlopen(_req, timeout=10)
                        app_logger.info(f"Dashboard updated: {_payload.decode()}")
        except Exception as _e:
            app_logger.warning(f"Dashboard update failed (non-critical): {_e}")

    # Clear temporary working dir regardless on failure and success
    shutil.rmtree(workspace, ignore_errors=True)

    app_logger.info(f"Saved log file to {FGColor.WHITE}{Style.BOLD}{app_logger.filename}{FGColor.RESET}")
    return int(not flash_success)


if __name__ == "__main__":
    session_id = get_current_datetime_string_literal()

    parser = setup_argument_parser(session_id)

    args = parser.parse_args()
    flash_config = FlashConfig.from_args(args)

    sys.exit(main(flash_config, session_id))
