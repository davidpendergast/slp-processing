

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