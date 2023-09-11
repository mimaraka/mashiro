import datetime
from typing import Literal

LogType = Literal["info", "error"]

def mashilog(content, log_type: LogType="info"):
    if log_type == "error":
        type_text = "\033[1;31mERROR\033[m"
        content_ = f"\033[1;31m{content}\033[m"
    else:
        type_text = "\033[1;36mINFO\033[m"
        content_ = content

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"\033[1;90m{now_str}\033[m {type_text}\t\033[1;32m静山マシロ\033[m {content_}"
    print(log_text)
