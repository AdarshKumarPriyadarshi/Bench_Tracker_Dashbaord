from __future__ import annotations

import os
import re
from typing import List

from config.flash_config import FlashConfig
from log.logger import Logger
from log.print_logger import PrintLogger
from log.format import FGColor
from log.utils import dump_figlet_digital_txt, dump_time, get_current_datetime_string_literal
from utils.runtime import RuntimeTimer


class FlashGraph:
    """
    Holds everything that is necessary to perform a flashing of an e.g. IDC.

    The user can provide the actual flashing-workers/operators,
    which will be run in the same order.

    """

    def __init__(self, config: FlashConfig, logger: Logger, workdir=None):
        """Initializes internals from given valid inputs.
        NOTE: It is assumend that the input carries valid data.
              To provide valid input, the user is
              adviced to use createFromConfig.

        Args:
            config (dict):        Contains necessary information to succesfully run a flash procedure.
            logger (PrintLogger): Logger that dumps e.g. to console.
                                  NOTE: Any logger that support the interface of PringLogger
                                        will work (e.g. FileAndStreamLogger).
            workdir (path)      : Working directory for temporary file and data placement.
        """
        self.config = config
        self.workspace = config.output.workspace
        self.logger = logger
        self.workingDir = workdir

        if not os.path.exists(self.workingDir):
            raise FileExistsError(f"Expecting existing workspace directory: {self.workingDir}")

        # Holds array of flashing worker/operators:
        self.flashOps = []
        # Holds statistics of flashing process:
        self.flash_stats = []

    @classmethod
    def createFromConfig(cls, config: FlashConfig, *args, **kwargs) -> FlashGraph:
        """Create a FlashGraph with valid data from the given config and arguments.

        Args:
            config (dict): Contains configuration setup for IDC flashing,
                           that is data to flash, connection information etc.

        """

        # Check if a logger was provided, if not default to PrintLogger:
        logger: Logger = kwargs.get("logger", PrintLogger())

        if kwargs.get("workdir", None) is not None:
            workdir = kwargs["workdir"]
        else:
            # Working directory: Both are created, path and actual directory.
            workdir = str(config.output.workspace) + "/drburn-" + get_current_datetime_string_literal()
            # Make sure nothing is overwritten!
            have_workdir = safeMakeDir(workdir, logger=logger)
            if not have_workdir:
                workdir = createUniqueNumDir(workdir)
            logger.info(f"FlashGraph created working-directory: {workdir}")

        return cls(config, logger=logger, workdir=workdir)

    def addFlashOp(self, op):
        """Adding a flash-operator object, e.g. AdaptiveFlashOp.

        Args:
            op (FlashOp): A spezialized form of the FlashOp type.
        """
        assert hasattr(op, "name")
        assert hasattr(op, "flash")
        assert hasattr(op, "report")
        self.flashOps.append(op)

    def run(self) -> bool:
        """Runs all the given flash-operators in the order given by addFlashOp(..) function.

        Returns:
            True: If ALL flash-operations were conducted successfully.
            False otherwise.
        """

        self.logger.info(dump_figlet_digital_txt("Run Star-Flasher!"))

        if len(self.flashOps) == 0:
            self.logger.warning("[WARNING]  Nothing given for flashing!")
            return False

        flash_successes: List[bool] = []
        self.flash_stats = []
        nrFlashOps = len(self.flashOps)

        for idx, flashOp in enumerate(self.flashOps):

            with RuntimeTimer(flashOp.name) as run_time:
                # Run flashing:
                op_suc = flashOp.flash()

            flash_successes.append(op_suc)

            # Collect flash statistic:
            stats = FlashStatistics(type(flashOp).__name__, flashOp.name, op_suc, float(run_time), flashOp.report)
            self.flash_stats.append(stats)

            # If multiple flash-ops are provided, we expect ALL to succeed, otherwise we opt out.
            if not op_suc and idx < nrFlashOps - 1:
                self.logger.warning(f"FlashOp {type(flashOp).__name__} failed. -> Remaining flash-ops are ignored!")
                for k in range(idx + 1, len(self.flashOps)):
                    _op_name = self.flashOps[k].name
                    _op_type_name = type(self.flashOps[k]).__name__
                    self.logger.warning(f"Ignoring flash-op: {_op_name} (Type: {_op_type_name})")
                break

        # Success is reported if all ops are successfully run.
        return all(flash_successes)

    def print_summary(self):

        for stat in self.flash_stats:
            stat.dump(logger=self.logger)


class FlashStatistics:
    def __init__(self, type_name: str, name: str, success: bool, duration_sec: float, report_txt: str = "-"):
        self.type_name = type_name
        self.name = name
        self.success = success
        self.duration_sec = duration_sec
        self.report_txt = report_txt

    def dump(self, logger=PrintLogger()):

        duration_str = dump_time(self.duration_sec)

        # First create dictionary for easy printing:
        __info_dict = {
            "Flash Type": str(self.type_name),
            "Name of FlashOp.": str(self.name),
            "Flash result": BinaryResult(self.success),
            "Duration": duration_str,
        }
        if "\n" in self.report_txt:
            report_str_lst = self.report_txt.split("\n")
            __info_dict.update({"Report": report_str_lst[0]})
            for k in range(1, len(report_str_lst)):
                __info_dict.update({f"Reportn{k:03d}": report_str_lst[k]})
        else:
            __info_dict.update({"Report": self.report_txt})

        def dumpInfoDictAsTable(datadict, delimiter="|"):
            # TODO: (fgritsc) Clean up once dump_dict_as_table is generic enough.
            lhsTitle = "Property"
            rhsTitle = "Value"
            paddingLeft = 1
            paddingRight = 1  # left plus right
            lhsColWidth = max([len(str(e)) for e in list(datadict.keys())])
            rhsColWidth = max([len(str(e)) for e in list(datadict.values())])

            def columnHorLine(length, char="-"):
                return (paddingLeft + length + paddingRight) * char

            def horizontalLine(char="-"):
                return (
                    len(delimiter) * "o"
                    + columnHorLine(lhsColWidth, char)
                    + "o"
                    + str(columnHorLine(rhsColWidth, char))
                    + "o"
                )

            outstr = ""
            outstr += horizontalLine() + "\n"
            outstr += delimiter + paddingLeft * " " + f"{lhsTitle:<{lhsColWidth}}" + paddingRight * " "
            outstr += delimiter + paddingLeft * " " + f"{rhsTitle:<{rhsColWidth}}" + paddingRight * " "
            outstr += delimiter + "\n"
            outstr += horizontalLine() + "\n"
            for name, data in datadict.items():
                if "Reportn" in name:
                    name = " "
                outstr += delimiter + paddingLeft * " " + f"{name:<{lhsColWidth}}" + paddingRight * " "
                outstr += delimiter + paddingLeft * " " + f"{data:<{rhsColWidth}}" + paddingRight * " "
                outstr += delimiter + "\n"
            outstr += horizontalLine() + "\n"

            return outstr

        logger("Flash-Statistics")
        logger(dumpInfoDictAsTable(__info_dict))
        logger(" ")


class BinaryResult:
    def __init__(self, success):
        self._success = success
        self.__checkmark_str = "\u2705"
        self.__crossmark_str = "\u274c"

        # Parse success to string literal.
        if self._success:
            self._result_str = "SUCCESS "
        else:
            self._result_str = "FAILURE "

    def __str__(self):
        if self._success:
            return f"{FGColor.GREEN}{self._result_str}{FGColor.RESET}{self.__checkmark_str}"
        else:
            return f"{FGColor.RED}{self._result_str}{FGColor.RESET}{self.__crossmark_str}"

    def __format__(self, spec):
        # Correct for the icon-mark.
        new_spec = spec
        if "<" in spec:
            number_str = re.findall(r"\d+", spec)[0]
            full_length = len(str(self)) - len(self._result_str)
            new_number = int(number_str) + full_length - 2
            new_spec = spec.replace(number_str, f"{new_number}")

        return str(self).__format__(new_spec)

    def __len__(self):
        return len(self._result_str)


def safeMakeDir(directory, logger: Logger):
    """Creates a directory if it is not existing already.
    It safely checks after creating the directory, if creation
    was succesfull.

    Args:
        directory (str): new directory to create
        logger (Logger, optional): Logger instance. Defaults to PrintLogger().

    Returns:
        boolean: True if directory creation was successful, False otherwise.
    """
    # Check if already existing.
    try:
        os.mkdir(directory)
    # If folder already exists, something went wrong
    except FileExistsError as ferr:
        logger.error(ferr)
        # logger.error(f"Directory {directory} already exists.")
        return False
    # Double check:
    if os.path.isdir(directory):
        logger.info(f"Created directory: {directory}")
        return True
    else:
        logger.error(f"Created directory {directory} not found!")
        return False


def createUniqueNumDir(basedir):
    """
    Given a base directory, this function creates a numeric unique directory.
    Starts with
    000001
    and maximum is  999999

    E.g.
    Given basedir : 'MYBASE'

    ls MYBASE
    ~ MYBASE/000001
    ~ MYBASE/000002

    outdir = 000003

    """
    outdir = basedir

    for k in range(1000000):
        candidate_dir = basedir + f"{k:06d}"
        if os.path.exists(candidate_dir):
            pass
        else:
            os.makedirs(candidate_dir)
            outdir = candidate_dir
            break

    assert os.path.isdir(outdir), "Directory not existing!"
    return outdir
