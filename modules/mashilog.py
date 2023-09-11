import datetime
from typing import Literal

LogType = Literal["info", "error"]

def mashilog(content, log_type: LogType="info"):
    if log_type == "error":
        type_text = "\[\e[1;31m\]ERROR\[\e[m\]"
        content_ = f"\[\e[1;31m\]{content}\[\e[m\]"
    else:
        type_text = "\[\e[1;36m\]INFO\[\e[m\]"
        content_ = content

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"\[\e[1;90m\]{now_str}\[\e[m\] {type_text}\t\[\e[1;32m\]静山マシロ\[\e[m\] {content_}"
    print(log_text)
