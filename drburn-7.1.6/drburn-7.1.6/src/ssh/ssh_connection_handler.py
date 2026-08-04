from itertools import chain
from pathlib import Path
import paramiko
import platform
import scp
import signal
import subprocess
import sys
import traceback
import time
from typing import Union, Iterable, Tuple

from config.flash_config import FlashConfig
from log.logger import Logger
from log.print_logger import PrintLogger
from log.utils import dump_success
from ssh.dummy_clients import DummySCPClient, DummySSHClient


class SSHConnectionHandler:
    """Handler that organizes an SSH connection using paramiko module.
    The contextmanager decorator is implemented, i.e.

     __enter__
     __exit__

     methods are realized.

     Usage:

     with SSHandler(config=myConfig) as ssh:
         if ssh is None:
             return

         ssh.exec_command(....)

    NOTE: The SSHClient methods

           - exec_command
           - get_transport

         are forwarded  if ssh connection could be established successfully.

     ATTENTION: with(..) context returns None if no connection could be created.
                This needs to be handled by user.
    """

    # TODO: (vibenzi) add ip and port as arguments and not read from config dict
    def __init__(self, config: FlashConfig, retry_timeout: int = 0, logger: Logger = PrintLogger()):
        self.config = config
        self.retry_timeout = retry_timeout
        self.logger = logger
        self.ssh = None
        self.scpClientTYPE = scp.SCPClient
        self.transport = None
        self.user = "root"
        self.password = "root"

    def clone(self, logger):
        """Clones from an existing SSHHandler
        without having to enter the password again.
        The return type can be used within a new context, i.e.

        with SSHHandler.clone(other..)  as clonessh:
            ....

        Args:
            otherSSHHandler (SSHHandler): _description_
            logToConsole (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        sshClone = SSHConnectionHandler(config=self.config, logger=logger)
        sshClone.password = self.password
        return sshClone

    def shutdownHandler(self, signum, frame):
        self.logger.info("Script interrupted by user.")
        sys.exit(0)

    def scp_progress(self, filename, size, sent):
        print(
            "%s's progress: %.2f%%" % (str(filename, "utf-8"), float(sent) / float(size) * 100),
            end="\r",
        )

    def __enter__(self):
        # Setup signal handling first (e.g. for user abortion).
        signal.signal(signal.SIGINT, self.shutdownHandler)

        # Shorthand
        ip = self.config.idc.ip
        port = self.config.idc.port
        user = self.user

        #        self.ssh = DummySSHClient(logger=self.logger)
        #        self.scp = DummySCPClient(logger=self.logger)
        #        return self#.ssh

        SSHClientTYPE = paramiko.SSHClient
        SCPClientTYPE = scp.SCPClient

        # Uncomment the following two lines in case of dry runs/testing in development stage.
        if self.config.debug:
            SSHClientTYPE = DummySSHClient
            SCPClientTYPE = DummySCPClient

        def createSSHClient(TYPE):
            if TYPE == DummySSHClient:
                return DummySSHClient(logger=self.logger)
            elif TYPE == paramiko.SSHClient:
                return paramiko.SSHClient()

        def createSCPClient(TYPE, ssh, progress_functor):
            if TYPE == DummySCPClient:
                return DummySCPClient(logger=self.logger)
            elif TYPE == scp.SCPClient:
                return scp.SCPClient(
                    ssh.get_transport(), progress=progress_functor, sanitize=lambda x: x, socket_timeout=300
                )

        self.ssh = createSSHClient(SSHClientTYPE)
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
        self.transport = self.ssh.get_transport()
        self.get_transport = self.ssh.get_transport

        # Ping is done to inform user if even ping was not possible.
        ping_success = ping(ip)

        if ping_success:
            self.logger.info(f"{dump_success()} ping {ip}")
        else:
            self.logger.warning(f"Ping {ip} without response from host!")

        self.logger.info(f"SSH: Connecting to {ip} on port {port}")
        connect_start_time = time.time()
        retry_interval = 20
        retry = False
        exception = None
        while (not retry) or (time.time() - connect_start_time) < self.retry_timeout:
            if retry:
                self.logger.info("Retrying...")
                time.sleep(retry_interval)
            try:
                # fmt:off
                self.ssh.connect(hostname=ip,
                                port=port,
                                username=user,
                                password=self.password,
                                banner_timeout=200,
                                timeout=120)
                # fmt:on
                self.logger.info(f"{dump_success()} SSH: Connected")
                self.scp = createSCPClient(SCPClientTYPE, self.ssh, self.scp_progress)  # type: scp.SCPClient
                return self

            except paramiko.AuthenticationException as e:
                self.logger.error("SSH: Authentication failed. Wrong username or password!")
                exception = e
                break

            except paramiko.SSHException as e:
                self.logger.critical("SSH: Server not reachable!")
                exception = e
                retry = True

            except paramiko.ssh_exception.NoValidConnectionsError as e:
                self.logger.critical(f"SSH: Unable to connect to {ip} on port {port}.")
                exception = e
                retry = True

            except Exception as e:
                exception = e
                break

        if exception is not None:
            self.logger.critical(str(exception))
            return None

        return None

    def __exit__(self, exc_type, exc_value, tb):
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, tb)
            # return False # uncomment to pass exception through

        if self.ssh:
            self.ssh.close()
        else:
            self.logger.debug(f"SSH: No connection to close!")

        return True

    def uploadToDevice(self, copy_from: Union[Path, Iterable[Path]], copy_to: Path):
        """Convenience method , copying file to device.

        Args:
            copy_from (Path): _description_
            copy_to (Path): _description_
            logger (_type_, optional): _description_. Defaults to print.
        """

        if not isinstance(copy_from, Iterable):
            assert copy_from.exists(), f"Path {copy_from} does not exist."
        assert copy_to is not None, f"Missing path {copy_to}."
        self.logger.info(f"SCP: from HOST    {copy_from}")
        self.logger.info(f"     to   Device  {copy_to}")
        self.scp.put(copy_from, str(copy_to), recursive=True, preserve_times=True)
        self.exec_command("sync")
        self.logger.info(f"SCP: File copied successfully.")

    def downloadFromDevice(self, copyFrom=None, copyTo=None):
        assert copyFrom is not None

        self.logger.info(f"SCP: from Device  {copyFrom}")
        self.logger.info(f"     to   HOST    {copyTo}")
        self.scp.get(copyFrom, copyTo, preserve_times=True)
        self.logger.info(f"SCP: File copied successfully.")
        self.logger.info(" ")

    def exec_command(self, cmd: str, verbose: bool = False, **kwargs) -> Tuple[bool, str, str]:
        """
        Executes command via ssh.

                Parameters:
                        ssh (SSHHandler): ssh handler
                        cmd (str): command to be executed
                        verbose (bool): print stdout

                Returns:
                        success (bool): boolean indicating whether command was
                                        successfully executed based on stderr output
                        stdout (str): stdout string
                        stderr (str): stderr string
        """
        _, stdout, stderr = self.ssh.exec_command(cmd, **kwargs)

        stdout_str = ""
        for line in iter(stdout.readline, ""):
            stdout_str += line
            if verbose:
                self.logger.info(line)

        stderr_str = str(stderr.read(), "utf-8")
        if verbose:
            self.logger.error(stderr_str)
            if stderr_str:
                return False, stdout_str, stderr_str

        exit_status = stdout.channel.recv_exit_status()

        return exit_status == 0, stdout_str, stderr_str


def ping(host: str) -> bool:
    """
    Returns True if host responds to a ping request once.
    NOTE: A 'ping' is not a reliable proof that a host is NOT availble.
        If the ICMP port on host side is disabled, the host does NOT respond
        but may be available e.g. ssh.
    """

    # Arg for the number of packets to send.
    if platform.system().lower() == "windows":
        param = "-n"
    else:
        # Unix like system.
        param = "-c"

    sh_command = ["ping", param, "1", host]
    timeout_secs = 30

    try:
        proc_res = subprocess.run(sh_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout_secs)
    except subprocess.TimeoutExpired as te:
        # Catch timeout.
        return False

    return proc_res.returncode == 0
