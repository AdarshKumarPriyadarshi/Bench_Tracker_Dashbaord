import socket
from getpass import getuser


class HostPC:
    @staticmethod
    def is_ds_pc():
        return "dspc" in socket.gethostname()

    @staticmethod
    def is_MTTF():
        return getuser() in ["gatewayuser", "emtc_its_s_mttflocal"]
