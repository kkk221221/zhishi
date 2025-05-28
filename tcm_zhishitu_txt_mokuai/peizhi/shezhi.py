import os

# Base directory for the module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This should resolve to tcm_zhishitu_txt_mokuai

# Data directory
DATA_DIR = os.path.join(BASE_DIR, "shuju")

# Entity filenames
YAOCAI_FILE = os.path.join(DATA_DIR, "shiti", "yaocai.txt")
ZHENGZHUANG_FILE = os.path.join(DATA_DIR, "shiti", "zhengzhuang.txt")
FANGJI_FILE = os.path.join(DATA_DIR, "shiti", "fangji.txt")

# Relationship filenames
YAOCAI_ZHENGZHUANG_GUANLIAN_FILE = os.path.join(DATA_DIR, "guanxi", "yaocai_zhengzhuang_guanlian.txt")

# Metadata filenames
SHUJU_LAIYUAN_FILE = os.path.join(DATA_DIR, "yuanshuju", "shuju_laiyuan.txt")

# ID Prefixes
YAOCAI_PREFIX = "YC"
ZHENGZHUANG_PREFIX = "ZZ"
FANGJI_PREFIX = "FJ"
GUANXI_PREFIX = "GX" # For general relationships, or define more specific ones
