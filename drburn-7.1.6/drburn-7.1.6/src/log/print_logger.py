# This logger forwards all logging querys to the print(..) command,
# eventually it can be used as drop in replacement for log.Logger types.
from log.logger import Logger


class PrintLogger(Logger):
    def __call__(self, *args, **kwargs):
        self.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        print("[DEBUG] ", end="")
        print(*args, **kwargs)

    def info(self, *args, **kwargs):
        print("[INFO] ", end="")
        print(*args, **kwargs)

    def warning(self, *args, **kwargs):
        print("[WARNING] ", end="")
        print(*args, **kwargs)

    def error(self, *args, **kwargs):
        print("[ERROR] ", end="")
        print(*args, **kwargs)

    def critical(self, *args, **kwargs):
        print("[FATAL] ", end="")
        print(*args, **kwargs)
