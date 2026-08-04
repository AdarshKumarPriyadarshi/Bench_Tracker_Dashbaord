import shutil

from log.utils import dump_bytes
from system.utils import bytes_to_gb, bytes_to_kb, bytes_to_mb


class DiskSpaceStatistics:
    __NORMAL_FILE_SIZE_GB = 10
    __STORAGE_ERROR_RELATIVE_FREE = 5.0 / 100.0
    __STORAGE_ERROR_ABSOLUTE_FREE_GB = 3 * __NORMAL_FILE_SIZE_GB
    __STORAGE_WARNING_RELATIVE_FREE = 20.0 / 100.0
    __STORAGE_WARNING_ABSOLUTE_FREE_GB = 10 * __NORMAL_FILE_SIZE_GB

    def __init__(self, directory):
        self.directory = directory

        total, used, free = shutil.disk_usage(directory)
        self.total_bytes = total
        self.used_bytes = used
        self.free_bytes = free

    def __str__(self):
        _total = dump_bytes(self.total_bytes)
        _used = dump_bytes(self.used_bytes)
        _free = dump_bytes(self.free_bytes)
        _dir = self.directory
        return f"Disk space statistics at ({_dir}):\nTotal = {_total} |  Used: {_used} |  Free: {_free}"

    @property
    def totalGB(self):
        return bytes_to_gb(self.total_bytes)

    @property
    def totalMB(self):
        return bytes_to_mb(self.total_bytes)

    @property
    def totalKB(self):
        return bytes_to_kb(self.total_bytes)

    @property
    def usedGB(self):
        return bytes_to_gb(self.used_bytes)

    @property
    def usedMB(self):
        return bytes_to_mb(self.used_bytes)

    @property
    def usedKB(self):
        return bytes_to_kb(self.used_bytes)

    @property
    def freeGB(self):
        return bytes_to_gb(self.free_bytes)

    @property
    def freeMB(self):
        return bytes_to_mb(self.free_bytes)

    @property
    def freeKB(self):
        return bytes_to_kb(self.free_bytes)

    @property
    def relativeFree(self):
        return self.free_bytes / self.total_bytes

    @property
    def diskSpaceWarning(self) -> str:
        if (self.relativeFree > DiskSpaceStatistics.__STORAGE_WARNING_RELATIVE_FREE) and (
            self.freeGB > DiskSpaceStatistics.__STORAGE_WARNING_ABSOLUTE_FREE_GB
        ):
            return None
        return f"\nLITTLE DISK SPACE AVAILABLE - ONLY {self.freeGB} GB ({self.relativeFree * 100}%) REMAINING IN {self.directory}\n"

    @property
    def diskSpaceError(self) -> str:
        if self.freeGB > DiskSpaceStatistics.__STORAGE_ERROR_ABSOLUTE_FREE_GB:
            return None
        return f"\nNOT ENOUGH DISK SPACE - ONLY {self.freeGB} GB ({self.relativeFree * 100}%) REMAINING IN {self.directory}\n"
