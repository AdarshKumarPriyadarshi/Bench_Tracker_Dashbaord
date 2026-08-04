import tarfile

from config.flash_config import FlashConfig, Source
from flashing.adaptive.adaptive_flash_op import AdaptiveFlashOp
from flashing.flash_graph import FlashGraph
from log.print_logger import PrintLogger


def test_adaptive_flash_op_create(tmp_path):
    # Given
    config = FlashConfig.from_default()

    workdir = tmp_path / "workdir"
    workdir.mkdir()

    logger = PrintLogger()
    flash_graph = FlashGraph(config=config, logger=logger, workdir=workdir)

    adaptive_tar = tmp_path / 'adaptive_partition_tar.tar'
    tarfile.open(adaptive_tar, 'a').close()

    persistency_tar = tmp_path / 'persistency_partition_tar.tar'
    tarfile.open(persistency_tar, 'a').close()

    stub_libs_tar = tmp_path / 'stub_libs_partition_tar.tar'
    tarfile.open(stub_libs_tar, 'a').close()

    sources = {
        "adaptive": Source(url=f"{adaptive_tar}"),
        "persistency": Source(url=f"{persistency_tar}"),
        "stub_libs": Source(url=f"{stub_libs_tar}"),
    }

    adaptive = config.modules["adaptive"]
    adaptive.update = True
    adaptive.sources = sources

    # When
    flash_op = AdaptiveFlashOp.create(flash_graph)

    # Then
    assert flash_op is not None
    assert isinstance(flash_op, AdaptiveFlashOp)
