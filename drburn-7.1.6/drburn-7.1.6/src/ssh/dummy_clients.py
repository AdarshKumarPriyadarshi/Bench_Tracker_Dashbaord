import io
from log.format import BGColor, FGColor, Style
from log.logger import Logger
from log.print_logger import PrintLogger


class FakeStdIO(io.StringIO):

    #    def __init__(self):

    def read(self, *args, **kwargs):
        self.seek(0)
        return bytes(self.getvalue(), "utf-8")


class DummySSHClient:
    class FakeIDC:
        # TODO: State machine:

        def __init__(self, logger: Logger = PrintLogger()):
            self.logger = logger
            self.adaptiveSTATE = "running"

        @property
        def prefix_literal(self):
            return f"{FGColor.VIOLETT}FakeIDC{FGColor.RESET}:"

        def update_with_cmd(self, cmd):
            if "adaptive/kill.sh" in cmd:

                self.logger.info(f"{self.prefix_literal} State transition:  running --> dead        (cmd = {cmd})")
                if self.adaptiveSTATE == "running":
                    self.adaptiveSTATE = "dead"
                else:
                    self.logger.info(f"{self.prefix_literal} [Already dead]  dead        (cmd = {cmd})")

                self.adaptiveSTATE = "dead"

            elif "adaptive/startup.sh" in cmd:
                self.logger.info(f"{self.prefix_literal} State transition:  dead --> running       (cmd = {cmd})")
                if self.adaptiveSTATE == "running":
                    self.logger.info(f"{self.prefix_literal} [Already running] running   (cmd = {cmd})")
                elif self.adaptiveSTATE == "dead":
                    self.adaptiveSTATE = "running"

        def get_pidin_arg(self):

            dummyStdin = FakeStdIO("dummyStdin")
            dummyStderr = FakeStdIO("dummyStderr")

            if self.adaptiveSTATE == "running":
                dummyStdout = FakeStdIO("X6m\nX6A\nX6ama")
            elif self.adaptiveSTATE == "dead":
                dummyStdout = FakeStdIO("")
            else:
                raise ValueError("Unknown idc state!")

            return dummyStdin, dummyStdout, dummyStderr

    # =======================================================

    def __init__(self, logger: Logger = PrintLogger(), *args, **kwargs):
        self.logger = logger
        # Fake IDC:
        self.idc = self.FakeIDC(logger=self.logger)

    @property
    def prefix_literal(self):
        return f"{FGColor.BLACK}{BGColor.WHITE}DummySSHClient::{FGColor.RESET}"

    def exec_command(self, *args, **kwargs):

        self.logger.info(f"{self.prefix_literal}exec_command(args={args}, kwargs={kwargs})")

        self.idc.update_with_cmd(args[0])

        dummyStdin = FakeStdIO("dummyStdin")
        dummyStderr = FakeStdIO("dummyStderr")
        dummyStdout = FakeStdIO("dummyStdout")

        if "pidin arg | grep -E 'X6|amsr|some|stub" in args[0]:
            return self.idc.get_pidin_arg()
        elif "if [ -z " in args[0]:
            return dummyStdin, FakeStdIO("EMPTY"), FakeStdIO("dummyStderr")
        elif "ls -d /usr/local/" in args[0] and "grep" in args[0]:
            return dummyStdin, FakeStdIO("driveworks-5.10"), FakeStdIO("dummyStderr")
        elif "then echo TRUE" in args[0]:
            return dummyStdin, FakeStdIO("TRUE"), FakeStdIO("dummyStderr")

        return dummyStdin, dummyStdout, dummyStderr

    def set_missing_host_key_policy(self, *args, **kwargs):
        self.logger.info(f"{self.prefix_literal}set_missing_host_key_policy")

    def connect(self, *args, **kwargs):
        self.logger.info(f"{self.prefix_literal}connect")

    def get_transport(self, *args, **kwargs):
        self.logger.info(f"{self.prefix_literal}get_transport")

    def close(self, *args, **kwargs):
        self.logger.info(f"{self.prefix_literal}close")


class DummySCPClient:
    def __init__(self, logger: Logger = PrintLogger, sanitize=None):
        self.logger = logger

    @property
    def prefix_literal(self):
        return f"{FGColor.BLACK}{BGColor.WHITE}{Style.ITALIC}DummySCPClient::{FGColor.RESET}"

    def put(self, fromFilename, toFilename, recursive=True, preserve_times=True):
        _prefix_whitespace = " " * len("DummySCPClient::")
        self.logger.info(f"{self.prefix_literal} [Download] From: {fromFilename}")
        self.logger.info(f"{_prefix_whitespace}         -> To  : {toFilename}")

    def get(self, fromDevice, toHost, preserve_times=True):
        self.logger.info(f"{self.prefix_literal} [Upload  ] To: {toHost}   <- From: {fromDevice}")
