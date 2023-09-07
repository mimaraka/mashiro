# Discordの文字装飾のエスケープ
def escape_markdown(text: str):
    result = ""
    for c in text:
        if c in ["*", "`", "\\", "~", "|"]:
            result += "\\"
        result += c
    return result