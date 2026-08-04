import pathlib
import sys
import tempfile

APP_NAME = "drburn"
DEFAULT_TMP_DIR = pathlib.Path(tempfile.gettempdir()).absolute() / "drburn"  # The working space parent folder
DEFAULT_DDU_FLASH_SCRIPT = pathlib.Path(sys._MEIPASS) / "src/flashing/ddu/flash_ddu.sh" if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS') else pathlib.Path(f"{ pathlib.Path(__file__).parent.parent}/flashing/ddu/flash_ddu.sh")
