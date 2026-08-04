import datetime


def bytes_to_gb(bytes: int):
    return bytes / (2**30)


def bytes_to_mb(bytes: int):
    return bytes / (2**20)


def bytes_to_kb(bytes: int):
    return bytes / (2**10)
