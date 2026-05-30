import typing
import re


def progress_bar(current, total, bar_width, bonus_text=""):
    pcnt = max(0.0, min(1.0, current / total))
    pcnt_text = f"{100 * pcnt:.1f}%"
    if len(pcnt_text) < 6:
        pcnt_text = " " * (6 - len(pcnt_text)) + pcnt_text

    bar_inner = '=' * int(pcnt * bar_width) + ' ' * (bar_width - int(pcnt * bar_width))
    bar = f"{pcnt_text} DONE [{bar_inner}] {bonus_text}"

    print(bar, end="\r")


def ask_yes_or_no_question(question):
    print("")
    answer = None
    while answer is None:
        txt = input("  " + question + " (y/n): ")
        if txt == "y" or txt == "Y":
            answer = True
        elif txt == "n" or txt == "N":
            answer = False
    print("")
    return answer


def ms_to_timestamp(duration_ms) -> str:
    duration_secs = int(duration_ms / 1000)
    if duration_secs > 3600:
        return (f"{duration_secs // 3600}h"
                f"{str((duration_secs % 3600) // 60).zfill(2)}m"
                f"{str(duration_secs % 60).zfill(2)}")
    else:
        return f"{duration_secs // 60}m{str(duration_secs % 60).zfill(2)}"


def ms_to_stadium_timestamp(duration_ms) -> str:
    if duration_ms > 60_000:
        return ms_to_timestamp(duration_ms)
    else:
        secs = duration_ms // 1000
        ms = duration_ms - secs * 1000
        if ms >= 995:
            secs += 1
            ms = 0
        return f"{str(secs).zfill(2)}s{str(round(ms / 10)).zfill(2)}"


def natsort(str_list: typing.List[str], key=lambda x: x) -> typing.List[str]:
    def _split_preserving_numbers(text):
        items = re.split(r'([^0-9]+)', text)
        ret = []
        for item in items:
            try:
                ret.append((0, int(item)))
            except ValueError:
                ret.append((1, item))
        return ret

    return list(sorted(str_list, key=lambda x: _split_preserving_numbers(key(x))))
