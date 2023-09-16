# Discordの文字装飾のエスケープ
def escape_markdown(text: str):
    result = ""
    for c in text:
        if c in ["*", "`", "\\", "|"]:
            result += "\\"
        result += c
    return result


def make_duration_text(sec: int):
    h = sec // 3600
    m = (sec - h * 3600) // 60
    s = sec % 60
    if h:
        result = f"{h}:{str(m).zfill(2)}:{str(s).zfill(2)}"
    else:
        result = f"{m}:{str(s).zfill(2)}"
    return result