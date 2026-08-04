import collections
import datetime
import pyfiglet

from log.format import Style, BGColor, FGColor
from system.utils import bytes_to_gb, bytes_to_kb, bytes_to_mb


def dump_bold(txt):
    return f"{Style.BOLD}{txt}{FGColor.RESET}"


def dump_success():
    return f"{FGColor.GREEN}{Style.BOLD}SUCCESS{FGColor.RESET}"


def dump_failure():
    return f"{FGColor.WHITE}{BGColor.RED}{Style.BOLD}FAILURE{FGColor.RESET}"


def dump_bytes(bytes: int):
    kilobytes = bytes_to_kb(bytes)
    megabytes = bytes_to_mb(bytes)
    gigabytes = bytes_to_gb(bytes)

    if kilobytes < 2:  # 0 ..... 2047 bytes
        return f"{bytes:3f} bytes"
    if megabytes < 2:  # 2048 ..... 2**20 * 2 < 1
        return f"{kilobytes:3f} kB"
    if gigabytes < 2:  #      ....... 2GB
        return f"{megabytes:3f} MB"
    return f"{gigabytes:3f} GB"


def dump_colored_figlet_txt(text, width=120, fgcolor=FGColor.WHITE, bgcolor=BGColor.BLACK):
    figl_renderer = pyfiglet.Figlet(width=120)
    figl_str = str(figl_renderer.renderText(text))
    return "".join([f"{fgcolor}{bgcolor}{row}{FGColor.RESET}\n" for row in figl_str.split("\n")])


def dump_dict_as_table(datadict, delimiter=" | "):
    if not datadict:
        return ""

    outstr = ""
    width = max([len(key) for key in datadict.keys()])

    def value_as_str(value):
        if not value:
            return "-"
        elif isinstance(value, bool):
            if value:
                return "True"
            else:
                return "False"
        elif isinstance(value, list):
            return ", ".join([str(elem) for elem in value])
        return str(value)

    for key, value in datadict.items():
        key_str = key + "".join((width - len(key)) * [" "])
        value_str = ""
        if value is not None:
            if isinstance(value, dict) or isinstance(value, collections.defaultdict):
                value = dict(value)
                value_str = f"\n{delimiter}{''.join(width * [' '])}\t{delimiter}".join(
                    [f"{key}: {value_as_str(value)}" for key, value in value.items()]
                )
            else:
                value_str = value_as_str(value)
        outstr += "\n" + delimiter + key_str + "\t" + delimiter + value_str
    if outstr:
        outstr += "\n"
    return outstr


# Helper for development:
def dump_figlet_digital_txt(txt):
    figlLogger = pyfiglet.Figlet(font="digital", width=120)
    return str(figlLogger.renderText(txt))


def dump_time(seconds: int, short: bool = False):
    if not seconds:
        return ""
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    h = "h" if short else "hour(s)"
    m = "m" if short else "minute(s)"
    s = "s" if short else "second(s)"

    if hours > 0.0:
        return f"{hours:.0f} {h} {minutes:.0f} {m} {seconds:.1f} {s}"
    elif minutes > 0.0:
        return f"{minutes:.0f} {m} {seconds:.1f} {s}"
    else:
        return f"{seconds:.1f} {s}"


def get_current_datetime_string_literal():
    # Create unique identifier string by datetime.
    currentDatetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
    return currentDatetime
