import os
import sys
import tarfile
from datetime import timedelta
from pathlib import Path
from timeit import default_timer
from typing import List


def get_tar_leading_dirs(tar_file: tarfile.TarFile) -> List[str]:
    common_path = str(os.path.commonpath(tar_file.getnames()))
    return [*Path(common_path).parts]


def tar_contains(tar_file: tarfile.TarFile, file: Path) -> bool:
    return any([file in name for name in tar_file.getnames()])


if __name__ == "__main__":
    # get_tar_leading_dirs assumes files are prefixes like
    # `tar cvzf ../rrdata_test.tgz trafficlightturning-hyperion8 --transform='s/^/rrdata\//'`

    with tarfile.open(sys.argv[1]) as archive:
        start = default_timer()
        leading_dirs = get_tar_leading_dirs(archive)
        print(Path(*leading_dirs))
        end = default_timer()
        print(timedelta(seconds=end - start))
