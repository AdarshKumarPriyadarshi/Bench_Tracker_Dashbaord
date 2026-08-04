from __future__ import annotations

import time
from os import PathLike
from typing import List

from log.logger import Logger
from log.print_logger import PrintLogger
from ssh.ssh_connection_handler import SSHConnectionHandler


class RemoteAdaptiveController:
    """
    Provides convenience functions to

    - stop adaptive on IDC
    - start  adaptive on IDc
    - mount adaptive partitions on IDC

    """

    def __init__(self, logger: Logger = PrintLogger()):
        self.logger = logger

    def get_active_adaptive_processes(self, ssh: SSHConnectionHandler) -> str:
        _X6RunningProcessCmd = """pidin arg | grep -E 'X6|amsr|some|stub'"""
        _, stdout, _ = ssh.exec_command(_X6RunningProcessCmd)
        return stdout

    def dump_active_adaptive_processes(self):
        return NotImplementedError

    def is_adaptive_running(self, ssh: SSHConnectionHandler) -> bool:
        running_adaptive_procs = self.get_active_adaptive_processes(ssh)
        return running_adaptive_procs.count("\n") > 1

    def get_number_of_active_adaptive_processes(self, ssh: SSHConnectionHandler) -> int:
        running_adaptive_procs = self.get_active_adaptive_processes(ssh)
        return len(running_adaptive_procs.splitlines())

    def stop(self, ssh: SSHConnectionHandler, verbose: bool = False) -> bool:
        ssh.exec_command("""/usr/adaptive/kill.sh 9""", verbose=verbose)

        # TODO: (fgritsc)
        # Adaptive consists of several processes with one
        # master process. If master process is terminated, all others
        # terminate as well.
        # However, there might be the case, that there are zombie processes.
        # In case of zombie processes, the following if case gets active
        # and a runtime error might be queried!
        # --> Catch all running processes and terminate them by hand!

        # Check if all adaptive processes were properly terminated
        if self.is_adaptive_running(ssh):
            self.logger.info("Failed to terminate adaptive stack.")
            return False

        return True

    def start(self, ssh: SSHConnectionHandler, timeout: int = 10) -> bool:
        if self.is_adaptive_running(ssh):
            self.logger.warning("ATTENTION: adaptive processes already running!")
            return True

        # NOTE: (fgritsc)
        # There is a problem with the query of the   /usr/adaptive/startup.sh
        # via remote/ssh since the /usr/badaptive/startup.sh itself calls some shell scripts
        # which causes some more processes being spawned.
        # Observation: The exec_command(..) does not terminate gracefully in time (timeout)
        # and thus an exception is thrown.
        # However, the adaptive is already started up successfully (checked in the sequel).
        # Proposal:
        # =========
        # One option to circumvent this behavior would be to read the /usr/adaptive/startup.sh
        # from the device/remote/idc and queyr line by line via the ssh - exec_command.
        # This way, each and every issued command is called separately which
        # may help tracking down some mal-/mis-behavior.
        try:
            ssh.exec_command("""/usr/adaptive/startup.sh & > /tmp/adaptive.log""", timeout=timeout)
        except:
            return False
            # See comment from above.

        # exponential backoff
        retries = 10
        delay = 1
        backoff = 1.1

        for retry in range(retries + 1):
            if retry:
                self.logger.info(f"Retrying adaptive startup in {delay:1.0f} seconds...")
                time.sleep(delay)

            nr_adaptive_procs = self.get_number_of_active_adaptive_processes(ssh)
            self.logger.info(f"Number of running adaptive processes on IDC: {nr_adaptive_procs}")

            # Check if adaptive processes were restarted
            if not self.is_adaptive_running(ssh):
                delay *= backoff
                continue
            else:
                self.logger.info("Restarted adaptive.")
                return True

        self.logger.warning("Failed to restart adaptive.")

        return False

    def mount_partitions(
        self,
        ssh: SSHConnectionHandler,
        partitions: List[str | PathLike],
    ):
        success = False

        for partition in partitions:
            max_nr_re_trials = 1
            trial_counter = 0

            while trial_counter <= max_nr_re_trials:
                trial_counter += 1

                self.logger.info(f"Mounting {partition} partition")
                _, stdout, stderr = ssh.exec_command(f"mount -uw {partition}")
                if len(stderr) > 0:
                    self.logger.info(f"Error in mounting the {partition} partition!")
                    self.logger.error(stderr)

                    continue

                success = True
                break

        return success
