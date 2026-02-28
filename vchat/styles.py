import shutil


def get_terminal_width():
    return shutil.get_terminal_size((80, 24)).columns


class S:
    RST      = '\033[0m'
    BOLD     = '\033[1m'
    DIM      = '\033[2m'
    ITALIC   = '\033[3m'
    ULINE    = '\033[4m'
    # 前景色
    BLACK    = '\033[30m'
    RED      = '\033[91m'
    GREEN    = '\033[92m'
    YELLOW   = '\033[93m'
    BLUE     = '\033[94m'
    MAGENTA  = '\033[95m'
    CYAN     = '\033[96m'
    WHITE    = '\033[97m'
    GRAY     = '\033[90m'
    # 背景色
    BG_BLACK = '\033[40m'
    BG_GRAY  = '\033[100m'
    BG_BLUE  = '\033[44m'
