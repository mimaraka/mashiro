import discord
import jaconv
import random
import re
import constants as const



# 正規表現を用いた少しゆるめの検索
def searchex(lis, target_text, strength, ignore_katahira=False, ignore_dakuten=False):
    TRANS_UL = str.maketrans("ぁぃぅぇぉっゃゅょゎ～", "あいうえおつやゆよわー")
    TRANS_DAKUTEN = str.maketrans("がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ", "かきくけこさしすせそだぢづでどはひふへほはひふへほ")
    # re.search()に用いるパターンの用意
    pattern = r""
    # リストの要素を取り出す
    for i, el in enumerate(lis):
        # リストの要素の型がリストであった場合(一文字ずつリストが用意されている)
        if type(el) == list:
            # 文字ごとの正規表現(〇|〇|...)を用意
            rchar = r""
            # リスト内の一単語ごとにforループ
            for j, s in enumerate(el):
                # 一文字ずつ正規表現に変換し、or記号(|)で区切る
                # 末端処理
                if j == len(el) - 1:
                    rchar += r"{}".format(s)
                else:
                    rchar += r"{}".format(s) + r"|"
            # 末端処理
            if i == len(lis) - 1:
                pattern += r"(" + rchar + r")"
            else:
                pattern += r"(" + rchar + r")" + r"((\s*|᠎*)*|.{," + r"{}".format(strength) + r"})"
        # リストの要素の型が文字列であった場合
        elif type(el) == str:
            # 文字列ごとの正規表現を用意
            rstr = r""
            # 文字列内の一文字ごとにforループ
            for j, c in enumerate(el):
                # 末端処理
                if j == len(el) - 1:
                    rstr += r"{}".format(c)
                else:
                    rstr += r"{}".format(c) + r"((\s*|᠎*)*|.{," + r"{}".format(strength) + r"})"
            # 末端処理
            if i == len(lis) - 1:
                pattern += r"(" + rstr + r")"
            else:
                pattern += r"(" + rstr + r")" + r"|"
        # リストの要素の型が上のいずれでもなかった場合
        else:
            return 0
    # 検索
    target = jaconv.kata2hira(target_text) if ignore_katahira else target_text
    target = target.lower().translate(TRANS_UL)
    if ignore_dakuten:
        target = target.translate(TRANS_DAKUTEN)
    return re.findall(pattern, target)



# 言葉狩り
async def kotobagari_proc(message: discord.Message):
    for _ in searchex(["ひつす", "必須"], str(message.content), 1, True):
        images = [const.URL_IMAGE_HISSU_01, const.URL_IMAGE_HISSU_02]
        await message.channel.send(random.choice(images))

    for _ in searchex(["あいす", "ちんこ", "ふえら"], str(message.content), 1, True):
        await message.channel.send(const.URL_IMAGE_ICECREAM)