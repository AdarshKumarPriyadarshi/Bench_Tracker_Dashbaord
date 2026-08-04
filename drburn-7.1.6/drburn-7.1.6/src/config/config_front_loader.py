import copy
import dataclasses
import datetime
import hashlib
import pathlib
from typing import List, Optional

import progressbar
import shutil
import subprocess
import tempfile
import time
import urllib

from config.flash_config import FlashConfig
from log.logger import Logger
from log.utils import dump_bytes, dump_dict_as_table, dump_time
from system.disk_space_statistics import DiskSpaceStatistics
from system.host_pc import HostPC
from utils.url import (
    PASSWORD_MANAGER,
    adapt_url_domain,
    authenticate,
    get_authentication_from_user,
    get_url_content_length,
    is_url,
    url_requires_authentication,
)


class ConfigFrontLoader:
    """Identifies URLs for the given binary flash blobs and transforms them to local paths.

    Therefore, the URLs are checked AND downloaded to the local storage path such
    that this binary becomes permanently available for the (local) user on a
    HIL or car system.
    """

    ERROR_KEY = "ERROR"
    __RETRIES = 5
    __RETRY_INTERVAL_SECONDS = 3
    __URL_SEPARATOR = "__"
    __WGET_NO_PROGRESS_AT_START_ERROR_SECONDS = 2
    __WGET_NO_PROGRESS_WARNING_SECONDS = 60  # 60
    __WGET_NO_PROGRESS_ERROR_SECONDS = 300  # 300

    @dataclasses.dataclass
    class SourceElem:
        config_root: FlashConfig
        module_id: str
        source_id: str
        original_url: str
        url: str
        debug: list
        error: list
        adapted_for_ds_pc: bool = None
        authorized: bool = False
        content_length: int = None
        hash: str = None
        existed: bool = False
        download_duration: int = None
        local_path: pathlib.Path = None

    @dataclasses.dataclass
    class File:
        prefix: str = None
        suffix: str = None

    def __init__(self, logger: Logger):
        self.logger = logger

    @classmethod
    def retrieve_url_elements_from_config(cls, config: FlashConfig) -> List[SourceElem]:
        url_elements: List[ConfigFrontLoader.SourceElem] = []

        for module_id, module in config.modules.items():
            for source_id, source in module.sources.items():
                if isinstance(source.url, str) and is_url(source.url):
                    config_elem = ConfigFrontLoader.SourceElem(
                        config_root=config, module_id=module_id, source_id=source_id, url=source.url,
                        original_url=cls.sanitize_url_elements(source.url), debug=[], error=[]
                    )
                    url_elements.append(config_elem)

        return url_elements

    @classmethod
    def sanitize_url_elements(cls, url: str) -> str:
        if not url or not url.startswith("http") or "artifact.swf.i.mercedes-benz.com" not in url:
            return url

        return url.replace("ui/native", "artifactory")

    @classmethod
    def retrieve_file_for_url(cls, url: str) -> File:
        """Creates a filename based on a given url preserving name and extension of the original file
        as required for instance for DDU flashing.

        Additionally, it adds a hash of the respective url surrounded by __URL_SEPARATOR allowing to re-use
        previously downloaded files.

        """
        file = cls.File()

        url_hash = ConfigFrontLoader.get_url_hash(url)

        # Retrieve filename. 'https://artifact.../bin_x86_linux..tar.gz' -> 'bin_x86_linux..tar.gz'
        name_and_extension = urllib.parse.urlparse(url.strip("/")).path.rpartition("/")[-1]
        name_and_extension_splits = name_and_extension.split(".")

        if len(name_and_extension_splits) > 1:
            name = name_and_extension_splits[0]
            extension = "." + ".".join(name_and_extension_splits[1:])
        else:
            name = name_and_extension_splits
            extension = None

        file.prefix = name + cls.__URL_SEPARATOR + url_hash + cls.__URL_SEPARATOR
        file.suffix = extension

        return file

    @classmethod
    def retrieve_url_hash_from_path(cls, path: pathlib.Path) -> Optional[str]:
        path_splits = path.stem.split(cls.__URL_SEPARATOR)
        if len(path_splits) == 3:
            return path_splits[1]
        else:
            return None

    @classmethod
    def get_url_hash(cls, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    @classmethod
    def download_url_using_wget(cls, logger: Logger, url: str, path: pathlib.Path, expected_file_size: int = None) -> str:
        """Downloads the given url to path.
        Returns the error string in case the download failed.
        Otherwise, None is returned.
        """
        # ToDo: How to handle user interruption?(Recursion)
        wget = shutil.which("wget") + " --continue"

        if not wget:
            logger.error(f"\n WGET NOT FOUND")
            raise RuntimeError("WGET is not installed")

        # wget command is dependent whether dspc is querying some bytes -> we can omit user and password
        if HostPC.is_ds_pc():
            # NOTE: Since not yet understood WHY the dspc aborts downloading after approx. 1GB
            #       workaround/hack -->    using   --continue flag to retrigger download
            wgetCmd = f"{wget} -O {path} {url}"
            logger.debug(wgetCmd)
        else:
            # Get user credentials.
            user, password = PASSWORD_MANAGER.find_user_password(None, url)
            # Wget download cmd.
            if user is not None and password is not None:
                wgetCmd = f"{wget} --user '{user}' --password '{password}' -O {path} {url}"
                logger.debug(f"{wget} --user '{user}' --password '********' -O {path} {url}")
            else:
                wgetCmd = f"{wget} -O {path} {url}"
                logger.debug(wgetCmd)

        try:
            CAPTURE_WGET_OUTPUT_TIMEOUT_SECONDS = 1.0
            WGET_OUTPUT_PROGRESS_SUBSTRING = ".........."  # .......... .......... .......... .........."
            wget_no_progress_interval = 0
            initial_file_size = path.stat().st_size
            previous_file_size = initial_file_size
            previous_time = time.time()
            wget_header = ""
            with subprocess.Popen(
                wgetCmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True
            ) as proc:
                if expected_file_size:
                    stdout = []
                    stderr = []

                    widgets = [
                        "Progress: ",
                        progressbar.Percentage(),
                        " ",
                        progressbar.GranularBar(),
                        # progressbar.Bar(marker=progressbar.RotatingMarker()),
                        " ",
                        progressbar.ETA(),
                        " ",
                        # progressbar.FileTransferSpeed(),
                        progressbar.widgets.Variable("download_speed", format="{formatted_value} / s"),
                    ]
                    with progressbar.ProgressBar(widgets=widgets, max_value=expected_file_size) as bar:
                        # Monitor file size
                        now = time.time()
                        file_size = path.stat().st_size
                        while file_size < expected_file_size:
                            time_interval = now - previous_time
                            file_size_diff = float(file_size - previous_file_size)
                            download_speed = file_size_diff / time_interval
                            # Accumulate time interval that file size has not changed
                            if file_size_diff == 0:
                                wget_no_progress_interval += time_interval
                                if (
                                    file_size == initial_file_size
                                    and wget_no_progress_interval
                                    >= ConfigFrontLoader.__WGET_NO_PROGRESS_AT_START_ERROR_SECONDS
                                ):
                                    proc.kill()
                                    return f"CONNECTION COULD NOT BE ESTABLISHED -- Download did not start for {dump_time(wget_no_progress_interval)}"
                                elif wget_no_progress_interval >= ConfigFrontLoader.__WGET_NO_PROGRESS_ERROR_SECONDS:
                                    proc.kill()
                                    return (
                                        f"CONNECTION HANG UP -- No progress for {dump_time(wget_no_progress_interval)}"
                                    )
                                elif wget_no_progress_interval >= ConfigFrontLoader.__WGET_NO_PROGRESS_WARNING_SECONDS:
                                    logger.info(
                                        f"No progress for {dump_time(wget_no_progress_interval)} -- Connection might have hung up"
                                    )
                            else:
                                wget_no_progress_interval = 0

                            try:
                                proc.communicate(timeout=CAPTURE_WGET_OUTPUT_TIMEOUT_SECONDS)
                            except subprocess.TimeoutExpired as e:
                                # NOTE: WGET does not output stdout
                                out = e.stdout
                                if out:
                                    out = out.decode("utf-8")
                                    logger.info(out)
                                    stdout.append(out)
                                err = e.stderr
                                if err:
                                    err = err.decode("utf-8").strip()
                                    stderr_lines = err.split("\n")
                                    # Re-output first lines of wget with download information
                                    stderr_first_progress_line_index = [
                                        index
                                        for index, line in enumerate(stderr_lines)
                                        if WGET_OUTPUT_PROGRESS_SUBSTRING in line
                                    ]
                                    # Header
                                    if stderr_first_progress_line_index:
                                        std_err_header = err.split(stderr_lines[stderr_first_progress_line_index[0]])[
                                            0
                                        ].strip()
                                    else:
                                        std_err_header = err

                                    # progress
                                    if not wget_header or (std_err_header != wget_header):
                                        if wget_header:
                                            wget_header_last_line = wget_header.split("\n")[-1]
                                            log_header = std_err_header.split(wget_header_last_line)[-1].strip()
                                        else:
                                            log_header = std_err_header
                                        if log_header:
                                            logger.info(log_header)
                                            wget_header += "\n" + std_err_header if wget_header else std_err_header
                                    if stderr_first_progress_line_index:
                                        bar.update(file_size, download_speed=dump_bytes(download_speed))
                                    else:
                                        # No progress - e.g. reconnect
                                        if err != wget_header:
                                            logger.info(err)
                                        wget_header = err.strip()
                            previous_time = now
                            previous_file_size = file_size
                            now = time.time()
                            file_size = path.stat().st_size
                        stdout, stderr = proc.communicate()

                else:
                    stdout, stderr = proc.communicate()
            logger.debug(stderr)
            result = subprocess.CompletedProcess(wgetCmd, proc.returncode, stdout, stderr)
            result.check_returncode()
        except subprocess.CalledProcessError as e:
            error = f"Failed to download {url}.\n'{wgetCmd}' did not terminate succesfully"
            if e.stderr:
                error += f"{e.stderr.strip()}"
            return error
        return None

    def run(self, config: FlashConfig):
        # DEEPCOPY CONFIG
        config_without_errors: FlashConfig = config.copy(deep=True)
        config_with_errors: FlashConfig = config.copy(deep=True)

        # URL ELEMENTS
        urls = ConfigFrontLoader.retrieve_url_elements_from_config(config_with_errors)

        if not len(urls):
            self.logger.debug(f"ConfigFrontLoader: Nothing to do")
            return config, config

        # LOCAL STORAGE
        localstorage = config.output.localstorage
        localstorage_stats = DiskSpaceStatistics(localstorage)
        self.logger.debug(str(localstorage_stats))
        disk_space_warning = localstorage_stats.diskSpaceWarning
        disk_space_error = localstorage_stats.diskSpaceError
        if disk_space_error:
            # Aborts if localstorage doesn't have enough free disk space
            self.logger.error(disk_space_error)
            self.logger.error(f"Aborting...")
            for url_source_elem in urls:
                url_source_elem.error.append(disk_space_error)
                # Add errors to config
                url_source_elem.config_root.modules[url_source_elem.module_id].sources[url_source_elem.source_id].error = True
            self.logger.info(dump_dict_as_table(config_with_errors))
            return config_without_errors, config_with_errors
        elif disk_space_warning:
            self.logger.info(disk_space_warning)

        # AUTHENTICATE
        user = config.artifactory.user
        password = config.artifactory.password
        if user and password:
            uri = config.artifactory.uri
            authenticate(user, password, uri) if uri else authenticate(user, password)

        for url_source_elem in urls:
            self.logger.info(f"Processing URL {url_source_elem.url}")
            # Adapt url
            if HostPC.is_ds_pc():
                self.logger.debug(f"Detected DS-PC environment")

                adapted_url = adapt_url_domain(url_source_elem.url)
                if adapted_url != url_source_elem.url:
                    self.logger.info(f"Adapted original URL")
                    self.logger.info(f"from {url_source_elem.url}")
                    self.logger.info(f"to {adapted_url}")
                    url_source_elem.adapted_for_ds_pc = True
                    url_source_elem.url = adapted_url
                    url_source_elem.config_root.modules[url_source_elem.module_id].sources[
                        url_source_elem.source_id].url = adapted_url
            url_hash = ConfigFrontLoader.get_url_hash(url_source_elem.url)
            url_source_elem.hash = url_hash
            self.logger.debug(f"Using hash {url_hash} as unique identifier for URL {url_source_elem.url}")
            # Verify authorization
            authorized = False
            attempts = self.__RETRIES + 1
            for attempt in range(attempts):
                try:
                    authorized = not url_requires_authentication(url_source_elem.url)
                    if not authorized and config.interactive:
                        self.logger.info("Authentication required")
                        credentials_attempts = self.__RETRIES + 1
                        for credentials_attempt in range(credentials_attempts):
                            user, password = get_authentication_from_user()
                            authenticate(user, password, url_source_elem.url)
                            authorized = not url_requires_authentication(url_source_elem.url)
                            if authorized:
                                break
                            else:
                                if credentials_attempt < credentials_attempts - 1:
                                    self.logger.error("Wrong user or password")
                                else:
                                    error_str = "Reached maximum number of credential fails"
                                    self.logger.error(error_str)
                                    url_source_elem.error.append(error_str)

                    break
                except Exception as e:
                    error_str = "Failed to verify authorization"
                    self.logger.error(error_str)
                    self.logger.error(f"{str(e)}")
                    if attempt < attempts - 1:
                        self.logger.info("Retrying...")
                        time.sleep(ConfigFrontLoader.__RETRY_INTERVAL_SECONDS)
                    else:
                        url_source_elem.error.append(error_str + " " + str(e))
            if authorized:
                url_source_elem.authorized = True
                self.logger.info(f"Verified authorization")
            else:
                error_str = "Not authorized"
                self.logger.error(f"{error_str}")
                url_source_elem.error.append(error_str)
                continue
            # Determine expected file size
            url_content_length = None
            attempts = self.__RETRIES + 1
            for attempt in range(attempts):
                try:
                    url_content_length = get_url_content_length(url_source_elem.url)
                    break
                except Exception as e:
                    error_str = f"Failed to determine content length"
                    self.logger.debug(error_str)
                    self.logger.debug(f"{str(e)}")
                    if attempt < attempts - 1:
                        self.logger.info("Retrying...")
                        time.sleep(ConfigFrontLoader.__RETRY_INTERVAL_SECONDS)
                    else:
                        url_source_elem.debug.append(error_str)
            if not url_content_length:
                self.logger.info(
                    f"Unable to check for previous downloads because content length of URL could not be determined"
                )
            else:
                self.logger.info(f"URL {url_source_elem.url} -- expected size {dump_bytes(url_content_length)}")
                url_source_elem.content_length = url_content_length
                # Check if url download exists already
                self.logger.info(f"Searching in {localstorage} for previous downloads")
                existing_files = [
                    path
                    for path in localstorage.iterdir()
                    if path.is_file() and (ConfigFrontLoader.retrieve_url_hash_from_path(path) == url_hash)
                ]
                if existing_files:
                    self.logger.info(f"Found {len(existing_files)} file(s):")
                    for file in existing_files:
                        stat = file.stat()
                        last_modified = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d_%H-%M-%S-%f")
                        self.logger.info(
                            f"{file.absolute()} -- size {dump_bytes(stat.st_size)} -- last modified {last_modified}"
                        )
                else:
                    self.logger.info(f"No previous download found")
                # Verify content length of existing files
                existing_files_with_correct_content_length = [
                    file for file in existing_files if file.stat().st_size == url_content_length
                ]
                if existing_files_with_correct_content_length:
                    self.logger.info(
                        f"{len(existing_files_with_correct_content_length)} / {len(existing_files)} file(s) have the expected size {dump_bytes(url_content_length)}:"
                    )
                    for file in existing_files_with_correct_content_length:
                        self.logger.info(f"{file.absolute()}")
                else:
                    if existing_files:
                        self.logger.info(f"No previous download matches the expected file size")
                # Remove existing incomplete files and duplicates
                incomplete_files = [
                    file for file in existing_files if not file in existing_files_with_correct_content_length
                ]
                duplicate_files = (
                    existing_files_with_correct_content_length[1:]
                    if len(existing_files_with_correct_content_length) > 1
                    else []
                )
                files_to_remove = incomplete_files + duplicate_files
                if files_to_remove:
                    self.logger.info(
                        f"Removing {len(files_to_remove)} duplicate or corrupt file(s) from {localstorage}"
                    )
                    for file in files_to_remove:
                        self.logger.info(f"Removing {file}")
                        file.unlink(missing_ok=True)
                # Use existing file
                if existing_files_with_correct_content_length:
                    # TODO: (vibenzi) Use file which was last modified
                    local_path = existing_files_with_correct_content_length[0]
                    self.logger.info(f"Using existing file {local_path}")
                    url_source_elem.existed = True
                    url_source_elem.local_path = local_path
                    url_source_elem.config_root.modules[url_source_elem.module_id].sources[
                        url_source_elem.source_id].url = local_path
                    continue
        # Download
        for index, url_source_elem in enumerate(urls):
            if url_source_elem.local_path or url_source_elem.error:
                continue
            # Check available disk space
            localstorage_stats = DiskSpaceStatistics(localstorage)
            disk_space_warning = localstorage_stats.diskSpaceWarning
            disk_space_error = localstorage_stats.diskSpaceError
            if disk_space_error:
                self.logger.error(disk_space_error)
                self.logger.error(f"Aborting due to low disk space -- {len(urls[index:])} file(s) not downloaded:")
                for remaining_url_source_elem in urls[index:]:
                    self.logger.info(f"{remaining_url_source_elem.url}")
                    remaining_url_source_elem.error.append(disk_space_error)
                break
            elif disk_space_warning:
                self.logger.info(disk_space_warning)
            # Retrieve file prefix and extension
            file = ConfigFrontLoader.retrieve_file_for_url(url_source_elem.url)
            download_successful = False
            local_path = None
            url_content_length = url_source_elem.content_length
            attempts = self.__RETRIES + 1
            temp_file = tempfile.NamedTemporaryFile(
                dir=localstorage, prefix=file.prefix, suffix=file.suffix, delete=False
            )
            local_path = pathlib.Path(temp_file.name)
            download_start_time = time.time()
            for attempt in range(attempts):
                if url_content_length:
                    self.logger.info(
                        f"Downloading {dump_bytes(url_content_length)} from {url_source_elem.url} to {localstorage}"
                    )
                else:
                    self.logger.info(f"Downloading URL {url_source_elem.url} to {localstorage}")
                # Download file using wget
                error_str = self.download_url_using_wget(self.logger, url_source_elem.url, local_path,
                                                         url_content_length)
                if error_str:
                    self.logger.error(error_str)
                    if attempt < attempts - 1:
                        self.logger.info("Retrying...")
                        time.sleep(ConfigFrontLoader.__RETRY_INTERVAL_SECONDS)
                        continue
                    else:
                        # Delete incomplete download
                        self.logger.debug(f"Removing corrupt file {local_path}")
                        local_path.unlink(missing_ok=True)
                        url_source_elem.error.append(error_str)
                        break
                if not local_path.is_file():
                    error_str = f"Downloaded file {local_path} not found"
                    self.logger.error(error_str)
                    if attempt < attempts - 1:
                        self.logger.info("Retrying...")
                        time.sleep(ConfigFrontLoader.__RETRY_INTERVAL_SECONDS)
                        continue
                    else:
                        url_source_elem.error.append(error_str)
                        break
                # Verify file size of downloaded file
                local_file_size = local_path.stat().st_size
                self.logger.info(f"{local_path} -- size {dump_bytes(local_file_size)}")
                if url_content_length:
                    if url_content_length == local_file_size:
                        download_successful = True
                        break
                    else:
                        error_str = f"Incomplete download. Only {dump_bytes(local_file_size)} / {dump_bytes(url_content_length)} downloaded"
                        self.logger.error(error_str)
                        if attempt < attempts - 1:
                            self.logger.info("Retrying...")
                            time.sleep(ConfigFrontLoader.__RETRY_INTERVAL_SECONDS)
                            continue
                        else:
                            # Delete incomplete download
                            self.logger.debug(f"Removing corrupt file {local_path}")
                            local_path.unlink(missing_ok=True)
                            url_source_elem.error.append(error_str)
                            break
                else:
                    error_str = (
                        "Unable to verify size of downloaded file because content length of URL could not be determined"
                    )
                    self.logger.debug(f"{error_str}")
                    url_source_elem.debug.append(error_str)
                    download_successful = True
                    break
            # Update config after successful download
            if download_successful:
                download_end_time = time.time()
                url_source_elem.local_path = local_path
                url_source_elem.download_duration = download_end_time - download_start_time
                url_source_elem.config_root.modules[url_source_elem.module_id].sources[
                    url_source_elem.source_id].url = local_path

        # Add errors to config_with_errors
        config_without_errors = copy.deepcopy(config_with_errors)
        FIELDS = ["url", "local_path", "content_length", "download_duration", "existed", "error"]
        USER_FRIENDLY_FIELDS = ["URL", "Path", "Size", "Download duration", "Existed", "Error"]
        for url_source_elem in urls:
            if url_source_elem.error:
                url_source_elem.config_root.modules[url_source_elem.module_id].sources[url_source_elem.source_id].error = True
            report_dict = {
                field.name: url_source_elem.__getattribute__(field.name)
                for field in dataclasses.fields(url_source_elem)
                if field.name in FIELDS
            }
            if "download_duration" in report_dict.keys() and report_dict["download_duration"]:
                report_dict["download_duration"] = dump_time(report_dict["download_duration"])
            if "content_length" in report_dict.keys() and report_dict["content_length"]:
                report_dict["content_length"] = dump_bytes(report_dict["content_length"])
            report_dict = {USER_FRIENDLY_FIELDS[FIELDS.index(key)]: value for key, value in report_dict.items()}
            self.logger.info(dump_dict_as_table(report_dict))

        return config_without_errors, config_with_errors
