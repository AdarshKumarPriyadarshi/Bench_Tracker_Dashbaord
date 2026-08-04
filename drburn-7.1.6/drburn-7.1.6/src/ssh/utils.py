import pathlib

from log.logger import Logger
from log.print_logger import PrintLogger
from ssh.ssh_connection_handler import SSHConnectionHandler


def erase_directory(ssh: SSHConnectionHandler, dir: pathlib.Path, retries=1, logger: Logger = PrintLogger()):
    try:
        ssh.exec_command(f"""rm -rf {dir}/*""")
        empty_str = "EMPTY"
        _, stdout, _ = ssh.exec_command(f"""if [ -z "$(ls -A {dir})" ]; then echo {empty_str}; fi""")
        is_path_empty = empty_str in stdout
        if not is_path_empty:
            logger.info(f"Failed to erase directory {dir}.")
            return False
    except:
        if retries:
            erase_directory(ssh, dir, retries - 1)
        else:
            return False
    return True


def is_directory(
    ssh: SSHConnectionHandler,
    dir: str,
) -> bool:
    true_str = "TRUE"
    cmd_is_directory = f"if [ -d {dir} ]; then echo {true_str}; fi"
    _, stdout, _ = ssh.exec_command(cmd_is_directory)
    if true_str in stdout.strip():
        return True
    else:
        return False


def remove_directory(
    ssh: SSHConnectionHandler,
    dir: str,
) -> bool:

    if is_directory(ssh, dir):
        ssh.logger.info(f"Removing directory {dir}")
        cmd_success, _, _ = ssh.exec_command(f"rm -rf {dir}")
        return cmd_success

    else:
        return False
