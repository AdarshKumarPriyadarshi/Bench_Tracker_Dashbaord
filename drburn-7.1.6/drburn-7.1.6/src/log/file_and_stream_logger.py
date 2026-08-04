import copy
import datetime
import json
import logging
import pathlib

from log.format import BGColor, FGColor
from log.logger import Logger


class FileAndStreamLogger(Logger):
    """Logs all given strings to console as well as file.

    Users have the chance to inspect the log message *after* the
    program/application terminated unexpected.
    The log-file also enables sharing information on
    inteded or uninteded behavior.
    """

    def __init__(self, logdir: pathlib.Path, name: str = "UndefinedLoggerName", debug: bool = False):
        super().__init__()
        # [Logger]
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # [STDOUT stream]
        streamer = logging.StreamHandler()
        streamer.setLevel(logging.DEBUG if debug else logging.INFO)
        formatter = ColoredLoggingFormatter("|%(asctime)s.%(msecs)03d| %(levelname)-17s| %(message)s", "%H:%M:%S")
        streamer.setFormatter(formatter)
        logger.addHandler(streamer)
        logger.addFilter(MultilineFilter())

        if not logdir.exists():
            print(f"Logging directory {logdir} does not exist.")
            raise FileNotFoundError

        self._filename = logdir / f"{name}.log"

        # [STDOUT file]
        fileio = logging.FileHandler(filename=self._filename)
        fileio.setLevel(logging.DEBUG)
        fileio.setFormatter(formatter)
        logger.addHandler(fileio)
        logger.addFilter(MultilineFilter())

        self.streamer = streamer
        self.fileio = fileio

        self.logger = logger

        self.logger.debug(f"Saving {name} log file to {self._filename}")
        self.logger.debug(f"Date and time at startup (UTC)  : {datetime.datetime.utcnow()}")
        self.logger.debug(f"Date and time at startup (local): {datetime.datetime.now()}")

    def __call__(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    @property
    def filename(self):
        return self._filename

    @classmethod
    def json_dumps(cls, json_obj) -> str:
        return json.dumps(json_obj, indent=4, default=str)

    def setConsoleLogLevel(self, loglevel):
        self.streamer.setLevel(loglevel)

    def setFileLogLevel(self, loglevel):
        self.fileio.setLevel(loglevel)

    def info(self, *args, **kwargs):
        self.logger.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self.logger.debug(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self.logger.warning(*args, **kwargs)

    def error(self, *args, **kwargs):
        self.logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        self.logger.critical(*args, **kwargs)


class MultilineFilter(logging.Filter):
    def filter(self, record):
        if not record.msg:
            return None
        if hasattr(record, "dct") and len(record.dct) > 0:
            for k, v in record.dct.iteritems():
                record.msg = record.msg + "\n\t" + k + ": " + v
        if record.msg.count("\n") > 1:
            indent = 10 * " "
            record.msg = "\n" + indent + record.msg.replace("\n", "\n" + indent)
        return super(MultilineFilter, self).filter(record)


class ColoredLoggingFormatter(logging.Formatter):
    """
    Formats the logging record with colors,
    e.g.   logger.error("my text") --->   "\red(ERROR)  mytext"

    """

    def __init__(self, pattern, *args, **kwargs):
        logging.Formatter.__init__(self, pattern, *args, **kwargs)

    def format(self, msg):
        color_msg = copy.copy(msg)
        levelname = color_msg.levelname
        # Log level to color table.
        color_coding = {
            "DEBUG": FGColor.WHITE,
            "INFO": FGColor.CYAN,
            "WARNING": FGColor.YELLOW,
            "ERROR": FGColor.RED,
            "CRITICAL": f"{FGColor.RED}{BGColor.WHITE}",
        }
        color_prefix = color_coding.get(levelname, FGColor.WHITE)
        color_levelname = f"{color_prefix}{levelname}{FGColor.RESET}"
        color_msg.levelname = color_levelname
        return logging.Formatter.format(self, color_msg)
