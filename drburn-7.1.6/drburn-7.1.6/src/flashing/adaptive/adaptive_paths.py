class AdaptivePaths:
    """Set of fixed specifications for the adaptive stack.
    This struct like type holds constant strings.
    """

    @property
    def ADAPTIVE_SOURCE(self):
        return "adaptive_partition_tar.tar"

    @property
    def ADAPTIVE_PERSISTENCY_SOURCE(self):
        return "persistency_partition_tar.tar"

    @property
    def ADAPTIVE_TARGET(self):
        return "/usr/adaptive"

    @property
    def ADAPTIVE_PERSISTENCY_TARGET(self):
        return "/var/lib/adaptive"
