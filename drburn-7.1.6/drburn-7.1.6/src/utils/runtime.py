import time


class RuntimeTimer:
    def __init__(self, name):
        self._name = name
        self.start_time = None
        self.stop_time = None

    @property
    def name(self):
        return self._name

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        self.stop_time = time.perf_counter()

    def __int__(self):
        return int(self.stop_time - self.start_time)

    def __float__(self):
        return float(self.stop_time - self.start_time)

    def __coerce__(self, other):
        return (float(self), other)

    def __str__(self):
        return str(float(self))

    def __repr__(self):
        return str(float(self))
