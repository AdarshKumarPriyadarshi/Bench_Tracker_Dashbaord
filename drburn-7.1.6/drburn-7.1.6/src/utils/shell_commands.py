#!/usr/bin/env python3

import typing

# Files
CHANGE_DIRECTORY = "cd {}"
CHECK_TRUE = "TRUE"
REMOVE_PATH = "rm -rf {}"
CLEAR_DIRECTORY_CONTENTS = "rm -rf {}/*"
CHECK_IS_DIRECTORY = "if [ -d {} ]; then echo {}; fi"
CHECK_IS_FILE = "if [ -f {} ]; then echo {}; fi"
CHECK_DIRECTORY_EMPTY = "if [ -z '$(ls -A {})' ]; then echo {}; fi"
GET_PATHS_MATCHING_REGEX = "ls -d {}/* | grep '{}'"
MOUNT_PARTITION_READ_WRITE = "mount -uw {}"

# Tar
EXTRACT_TAR = "tar -xvf {}"
EXTRACT_TAR_STRIP_COMPONENTS = " --strip-components={}"
CREATE_GZIP_COMPRESSED_TAR = "tar -czvf {} {}"
EXTRACT_GZIP_COMPRESSED_TAR = "tar -zxvf {}"
TAR_CHANGE_TO_ROOT = " -C /"

# Adaptive
GET_ACTIVE_ADAPTIVE_PROCESSES = "pidin arg | grep -E 'X6|amsr|some|stub'"
START_ADAPTIVE_PROCESSES = "/usr/adaptive/startup.sh"
KILL_ADAPTIVE_PROCESSES = "/usr/adaptive/kill.sh"


def remove_path(path: str) -> str:
    return REMOVE_PATH.format(path)


def clear_directory_contents(dir: str) -> str:
    return CLEAR_DIRECTORY_CONTENTS.format(dir)


def is_directory(path: str) -> str:
    return CHECK_IS_DIRECTORY.format(path, CHECK_TRUE)


def is_file(path: str) -> str:
    return CHECK_IS_FILE.format(path, CHECK_TRUE)


def change_directory(dir: str) -> str:
    return CHANGE_DIRECTORY.format(dir)


def is_directory_empty(dir: str) -> str:
    return CHECK_DIRECTORY_EMPTY.format(dir, CHECK_TRUE)


def is_return_true(stdout: str):
    return stdout.strip() == CHECK_TRUE


def get_paths_matching_regex(dir: str, regex: str):
    return GET_PATHS_MATCHING_REGEX.format(dir, regex)


def mount_partition(path: str) -> str:
    return MOUNT_PARTITION_READ_WRITE.format(path)


def extract_tar_file(dir: str, strip_components: int = 0) -> str:
    return (
        EXTRACT_TAR.format(dir) + EXTRACT_TAR_STRIP_COMPONENTS.format(strip_components)
        if strip_components
        else EXTRACT_TAR.format(dir)
    )


def create_gzip_compressed_tar_file(file: str, paths: typing.List[str]) -> str:
    return CREATE_GZIP_COMPRESSED_TAR.format(file, str.join(" ", paths))


def extract_gzip_compressed_tar_file(file: str, change_to_root: bool = False) -> str:
    return (
        EXTRACT_GZIP_COMPRESSED_TAR.format(file) + TAR_CHANGE_TO_ROOT
        if change_to_root
        else EXTRACT_GZIP_COMPRESSED_TAR.format(file)
    )
