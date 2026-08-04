from typing import Optional

from config.flash_config import FlashConfig
from flashing.adaptive.adaptive_flash_op import AdaptiveFlashOp
from flashing.ddu.bundle_flash_op import BundleFlashOp
from flashing.ddu.ddu_flash_op import DDUFlashOp
from flashing.flash_graph import FlashGraph
from flashing.ndas.ndas_flash_op import NDASFlashOp
from flashing.ndas.rrdata_flash_op import RRDATAFlashOp
from log.logger import Logger
from log.utils import dump_bold, dump_figlet_digital_txt


class FlashGraphCreator:
    """Creates a filled flash graph.
    The flash graph contains flashOps e.g. AdaptiveFlashOp, NDASFlashOp or DDUFlashOp.
    The config controls how to create and fill the flash graph.
    """

    def __init__(self, logger: Logger):
        self.logger = logger

    def createFlashGraph(self, config: FlashConfig) -> Optional[FlashGraph]:
        # ========================================================
        # FLASH GRAPH
        #  a) create flashing graph from config
        #  b) create flashing operators
        #    i)   AdaptiveFlashOp type
        #    ii)  NDASFlashOp type
        #    iii) DDUFlashOp type
        #    iv)  BundleFlashOp type
        #  c) Sort created flashing operators according to policy
        #  d) Add sorted flash operators to graph.
        # ========================================================

        # User info log.
        self.logger.info(dump_figlet_digital_txt("Create Flash-Graph!"))

        # a)
        fgraph = FlashGraph.createFromConfig(config, logger=self.logger, workdir=config.output.workspace)

        # b) Thanks to the factory, all ops are created there IFF possible.
        op_factory = FlashOpFactory(logger=self.logger)

        flash_op_lst_unsorted = op_factory.createFromGraph(fgraph)

        # Currently, we support only ONE object of op type (i.e. AdaptiveFlashOp, NDASFlashOp, DDUFlashOp..) per FlashGraph.
        #
        # Creation POLICY:
        # 1) Check there is at most one AdaptiveFlashOp/NDASFlashOp/DDuFlashOp given.
        # 2) Keep book of all provided/created ops' and sort them in the following (yet hardcoded) order:
        #
        # Abbreviation:
        # Adaptive (A)
        # NDAS     (N)
        # DDU      (D)
        # Bundle   (B)
        #
        # Table of given ops' and output order.
        #
        #   Ops'            | Order in output list
        #   -------------------------------------------
        #   A               | A
        #   N               | N
        #   D               | D
        #   B               | B
        #   -------------------------------------------
        #   A, N            | A, N
        #   A, D            | D, A
        #   N, D            | D, N
        #   N, B            | B, N
        #   D, B            | B, D
        #   -------------------------------------------
        #   A, N, D         | D, A, N
        #   A, B, D         | B, D, A
        #
        # We can conclude:   B is always first, then D, then A, then N

        # c) Sort and add.
        adaptive_ops = [op for op in flash_op_lst_unsorted if isinstance(op, AdaptiveFlashOp)]
        ndas_ops = [op for op in flash_op_lst_unsorted if isinstance(op, NDASFlashOp)]
        rrdata_ops = [op for op in flash_op_lst_unsorted if isinstance(op, RRDATAFlashOp)]
        # NOTE: Also considers derivatives of DDUFlashOp!
        ddu_ops = [op for op in flash_op_lst_unsorted if isinstance(op, DDUFlashOp)]
        bundle_ops = [op for op in flash_op_lst_unsorted if isinstance(op, BundleFlashOp)]

        nrAdaptiveOps = len(adaptive_ops)
        nrNDASOps = len(ndas_ops)
        nrRRDATAOps = len(rrdata_ops)
        nrDDUOps = len(ddu_ops)
        nrBundleOps = len(bundle_ops)

        if nrAdaptiveOps > 1:
            self.logger.error(
                f"FlashGraphCreator obtained more than 1 ({nrAdaptiveOps}) AdaptiveFlashOp objects. Config malformed."
            )
            return None

        if nrNDASOps > 1:
            self.logger.error(
                f"FlashGraphCreator obtained more than 1 ({nrNDASOps}) NDASFlashOp objects. Config malformed."
            )
            return None

        if nrRRDATAOps > 1:
            self.logger.error(
                f"FlashGraphCreator obtained more than 1 ({nrRRDATAOps}) RRDATAFlashOp objects. Config malformed."
            )
            return None

        if nrDDUOps > 1:
            self.logger.error(
                f"FlashGraphCreator obtained more than 1 ({nrDDUOps}) DDUFlashOp objects. Config malformed."
            )
            return None

        if nrBundleOps > 1:
            self.logger.error(
                f"FlashGraphCreator obtained more than 1 ({nrBundleOps}) BundleFlashOp objects. Config malformed."
            )
            return None

        # See creation policy (table) from comment above: 1. DDU  2. ADAPTIVE 3. NDAS 4. RRDATA
        flash_op_lst_sorted = []
        flash_op_lst_sorted.extend(bundle_ops)
        flash_op_lst_sorted.extend(ddu_ops)
        flash_op_lst_sorted.extend(adaptive_ops)
        flash_op_lst_sorted.extend(ndas_ops)
        flash_op_lst_sorted.extend(rrdata_ops)

        if len(flash_op_lst_sorted) < 1:
            self.logger.error(f"FlashGraphCreator could not create any FlashOp objects. Config malformed.")
            return None

        if len(flash_op_lst_sorted) > 3:
            self.logger.error(
                f"FlashGraphCreator created more than 3 FlashOp objects (undefined behavior). Config malformed."
            )
            return None

        # Now we have a sorted list of valid ops, that we append to the flash graph.
        info_str = ""
        nrFlashOps = len(flash_op_lst_sorted)
        for idx, flash_op in enumerate(flash_op_lst_sorted):
            fgraph.addFlashOp(flash_op)
            # Info log:
            info_str += type(flash_op).__name__
            if idx < nrFlashOps - 1:
                info_str += " => "
        self.logger.info(f"Order of flashing ops strategy: {info_str}")
        return fgraph


class FlashOpFactory:

    # List only base types.
    __default_node_types = [AdaptiveFlashOp, NDASFlashOp, RRDATAFlashOp, DDUFlashOp, BundleFlashOp]

    def __init__(self, logger, op_types=__default_node_types):
        self.__op_types = op_types
        self.logger = logger

    def createFromGraph(self, graph):

        ignored_types = []

        op_array = []
        for OP_TYPE in self.__op_types:
            op_node = OP_TYPE.create(graph)
            if op_node is None:
                ignored_types.append(OP_TYPE)
            else:
                op_array.append(op_node)

        for op_node in op_array:
            _op_type_name = f"{type(op_node).__name__:<18}"
            self.logger.info(f"Created FlashOp-type: {dump_bold(_op_type_name)} with name {op_node.name}")

        for ignored_type in ignored_types:
            self.logger.debug(f"FlashOp {ignored_type.__name__:<25}  not used.")

        return op_array
