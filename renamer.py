import os
import argparse
import traceback
import typing
import enum
import unicodedata
import shutil
import re

import utils

# need newer (unpublished) version of py_slippi, for skip_frames option.
import py_slippi.slippi as slippi  # py_slippi, parsing library for slp files


_FILTER_INCOMPLETE_SINGLE_PLAYER_GAMES = True


def calc_new_filename(fpath) -> typing.Tuple[typing.Union[str, None], str]:
    if not fpath.endswith('.slp'):
        return None, "ERROR"

    try:
        game = slippi.Game(fpath)
    except IOError as e:
        # try:
        #     # try to parse without frames - sometimes SLPs are corrupted
        #     # in such a way where the basic metadata can be parsed but
        #     # the frames can't. This means we can't get win/loss info
        #     # but better than nothing.
        #     game = slippi.Game(fpath, skip_frames=True)
        # except IOError:
        print(f"ERROR: failed to parse: {fpath}")
        traceback.print_exc()
        return None, "ERROR"

    if _should_filter(game):
        return None, "FILTERED"

    date = game.metadata.date.strftime('%Y%m%d')
    time = game.metadata.date.strftime('%H%M%S')

    players = []
    for idx in range(4):
        ptext = _get_player_text(game, idx)
        if ptext is not None:
            players.append(ptext)

    if len(players) == 2:
        player_text = f"{players[0]}_vs_{players[1]}"
    else:
        player_text = "_".join(players)  # dubs?

    if _is_stadium_mode(game):
        desc = _get_stadium_mode_desc(game)
    else:
        desc = _get_vs_mode_desc(game)

    return f"{date}T{time}_{player_text}{desc}.slp", "GOOD"


def _get_vs_mode_desc(game):
    gametime = utils.ms_to_timestamp(int(game.metadata.duration / 60 * 1000))
    stage = _get_stage_code(game.start.stage)

    if game.end.method == slippi.event.End.Method.NO_CONTEST:
        endstate = "_quit"
    elif game.end.method == slippi.event.End.Method.TIME:
        endstate = "_time"
    elif game.end.method == slippi.event.End.Method.INCONCLUSIVE:
        endstate = "_draw"
    else:
        endstate = ""

    return f"_{gametime}_{stage}{endstate}"


def _is_stadium_mode(game):
    # TODO should actually ID the stages
    return game.start.stage == slippi.id.Stage.UNKNOWN


def _is_btt(game):
    return len([p for p in game.start.players if p is not None]) == 1


def _is_hrc(game):
    return len([p for p in game.start.players if p is not None and p.character == slippi.id.CSSCharacter.SANDBAG]) == 1


def _get_stadium_mode_desc(game):
    mode = ""
    if _is_btt(game):
        # TODO can check stage ids of BTT stages
        mode = "_BTT"
    elif _is_hrc(game):
        mode = "_HRC"

    endstate = ""
    if game.end.method == slippi.event.End.Method.FAILURE:
        endstate = ""
    elif game.end.method == slippi.event.End.Method.RETRY:
        endstate = ""
    elif game.end.method in (slippi.event.End.Method.COMPLETE, slippi.event.End.Method.NEW_RECORD):
        if _is_btt(game):
            n_frames = game.metadata.duration - 124  # rm bonus frames before timer starts
            ms = round(n_frames / 60 * 1000)
        else:
            ms = round(game.metadata.duration / 60 * 1000)
        endstate = f"_{utils.ms_to_stadium_timestamp(ms)}"
    elif game.end.method == slippi.event.End.Method.NO_CONTEST:
        endstate = ""  # when sandbag gets zero distance

    return f"{mode}{endstate}"


def _should_filter(game):
    if _FILTER_INCOMPLETE_SINGLE_PLAYER_GAMES and _is_stadium_mode(game):
        return game.end.method in (slippi.event.End.Method.FAILURE,
                                   slippi.event.End.Method.RETRY,
                                   slippi.event.End.Method.NO_CONTEST)
    else:
        return False


STAGE_MAPPINGS = {
    slippi.id.Stage.BATTLEFIELD: "BF",
    slippi.id.Stage.DREAM_LAND_N64: "DL",
    slippi.id.Stage.FINAL_DESTINATION: "FD",
    slippi.id.Stage.FOUNTAIN_OF_DREAMS: "FoD",
    slippi.id.Stage.POKEMON_STADIUM: "PS",
    slippi.id.Stage.YOSHIS_STORY: "YS",
}


def _get_stage_code(stage_enum) -> str:
    if stage_enum in STAGE_MAPPINGS:
        return STAGE_MAPPINGS[stage_enum]
    else:
        return str(stage_enum.name)[:3]


CHAR_MAPPINGS = {  # shorten the long ones
    slippi.id.CSSCharacter.CAPTAIN_FALCON: "FALCON",
    slippi.id.CSSCharacter.DONKEY_KONG: "DK",
    slippi.id.CSSCharacter.DR_MARIO: "DOC",
    slippi.id.CSSCharacter.GAME_AND_WATCH: "GNW",
    slippi.id.CSSCharacter.GANONDORF: "GANON",
    slippi.id.CSSCharacter.ICE_CLIMBERS: "ICIES",
    slippi.id.CSSCharacter.JIGGLYPUFF: "PUFF",
    slippi.id.CSSCharacter.YOUNG_LINK: "YLINK"
}


def _get_character_code(char_enum) -> str:
    if char_enum in CHAR_MAPPINGS:
        return CHAR_MAPPINGS[char_enum]
    else:
        return str(char_enum.name)


CHAR_COLOR_MAPPINGS = {
    slippi.id.CSSCharacter.CAPTAIN_FALCON: ("", "BLACK", "RED", "PINK", "GREEN", "BLUE"),
    slippi.id.CSSCharacter.DONKEY_KONG: ("", "BLACK", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.FOX: ("", "ORANGE", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.GAME_AND_WATCH: ("", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.KIRBY: ("", "YELLOW", "BLUE", "RED", "GREEN", "WHITE"),
    slippi.id.CSSCharacter.BOWSER: ("", "RED", "BLUE", "BLACK"),
    slippi.id.CSSCharacter.LINK: ("GREEN", "RED", "BLUE", "BLACK", "WHITE"),
    slippi.id.CSSCharacter.LUIGI: ("GREEN", "WHITE", "BLUE", "PINK"),
    slippi.id.CSSCharacter.MARIO: ("RED", "YELLOW", "BROWN", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.MARTH: ("", "RED", "GREEN", "BLACK", "WHITE"),
    slippi.id.CSSCharacter.MEWTWO: ("", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.NESS: ("RED", "YELLOW", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.PEACH: ("PINK", "DAISY", "WHITE", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.PIKACHU: ("", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.ICE_CLIMBERS: ("BLUE", "GREEN", "ORANGE", "RED"),
    slippi.id.CSSCharacter.JIGGLYPUFF: ("", "RED", "BLUE", "GREEN", "CROWN"),
    slippi.id.CSSCharacter.SAMUS: ("ORANGE", "PINK", "BROWN", "GREEN", "PURPLE"),
    slippi.id.CSSCharacter.YOSHI: ("GREEN", "RED", "BLUE", "YELLOW", "PINK", "CYAN"),
    slippi.id.CSSCharacter.ZELDA: ("", "RED", "BLUE", "GREEN", "WHITE"),
    slippi.id.CSSCharacter.SHEIK: ("", "RED", "BLUE", "GREEN", "WHITE"),
    slippi.id.CSSCharacter.FALCO: ("", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.YOUNG_LINK: ("GREEN", "RED", "BLUE", "WHITE", "BLACK"),
    slippi.id.CSSCharacter.DR_MARIO: ("WHITE", "RED", "BLUE", "GREEN", "BLACK"),
    slippi.id.CSSCharacter.ROY: ("", "RED", "BLUE", "GREEN", "YELLOW"),
    slippi.id.CSSCharacter.PICHU: ("", "RED", "BLUE", "GREEN"),
    slippi.id.CSSCharacter.GANONDORF: ("", "RED", "BLUE", "GREEN", "PURPLE")
}


def _get_character_color_code(char_enum, color_id) -> str:
    if char_enum in CHAR_COLOR_MAPPINGS:
        ids = CHAR_COLOR_MAPPINGS[char_enum]
        if color_id < len(ids):
            return ids[color_id]
    return str(color_id)


def _get_player_text(game, port):
    pdata = game.start.players[port]
    if pdata is None:
        return None
    elif pdata.type != slippi.event.Start.Player.Type.HUMAN:  # 0:HUMAN
        return "CPU"
    else:
        portcode = f"(P{port + 1})"

        charcode = _get_character_code(pdata.character)
        colorcode = _get_character_color_code(pdata.character, pdata.costume)
        if len(colorcode) > 0:
            colorcode = f"({colorcode})"

        # tags use full-width chars, e.g. "ＧＨＳＴ", gotta normalize
        normalized_tag = unicodedata.normalize("NFKC", pdata.tag)
        tag = re.sub(r'[^a-zA-Z0-9 ]', '_', normalized_tag)  # alphanumeric only pls
        tag = f"({tag})" if len(tag) > 0 else ""

        winstate = ""
        if len(game.frames) > 0:
            lastframe = game.frames[-1]
            if lastframe.ports[port] is not None:  # sometimes this is null? unclear why/how
                stocks = lastframe.ports[port].leader.post.stocks
                winstate = f"({'L' if stocks == 0 else 'W'}{stocks})"

        return f"{portcode}{charcode}{colorcode}{tag}{winstate}"


def _lookup_enum(enum_cls, name) -> enum.IntEnum:
    for v in enum_cls:
        if v.name == name.upper():
            return v
    raise ValueError(f"Invalid token: {name} (must be one of: {[s.name for s in enum_cls]})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("slp renamer")
    parser.add_argument("-src", help="Root directory of raw slp files", type=str)
    parser.add_argument("-dest", help="directory to write the renamed files", type=str, required=False)

    args = parser.parse_args()
    src_dir = args.src
    if args.dest is not None:
        dest_dir = args.dest
    else:
        dest_dir = os.path.join(os.path.split(src_dir)[0], "renamed")
    print(f"\nWelcome to SLP Renamer\n  input directory: {src_dir}\n  output directory: {dest_dir}\n")

    unique_subdirs = set()
    all_slps = []
    for subdir, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".slp"):
                unique_subdirs.add(subdir)
                all_slps.append(os.path.join(subdir, file))
    print(f"Found {len(all_slps)} slp files in {len(unique_subdirs)} subdirectories.")

    print(f"\nCalculating new names...")

    fails = []  # files that failed to parse (can occur if wii is shutoff improperly)
    filtered = []
    renames = {}  # orig_filepath -> new_filepath
    for idx, fpath in enumerate(all_slps):
        new_fname, status = calc_new_filename(fpath)
        if new_fname is None:
            if status == "ERROR":
                fails.append(fpath)
                print(f"ERROR {fpath}")
            elif status == "FILTERED":
                filtered.append(fpath)
            else:
                print(f"ERROR: {fpath} (unexpected status: {status})")
        else:
            rel_fpath = os.path.relpath(fpath, src_dir)
            new_rel_fpath = list(os.path.split(rel_fpath))
            new_rel_fpath[-1] = new_fname
            renames[fpath] = os.path.join(*new_rel_fpath)
            print(f"{rel_fpath} -> {renames[fpath]}")

    delim = '\n  '
    if len(fails) > 0:
        print(f"\n{len(fails)} slp files couldn't be parsed (probably due to corruption):\n{delim.join(fails)}")

    if len(filtered) > 0:
        print(f"\n{len(filtered)} slp files were filtered.")

    proceed = utils.ask_yes_or_no_question(f"Copy {len(renames)} renamed files to {dest_dir}?")
    if not proceed:
        raise SystemExit

    all_created = []

    fail_cnt = 0
    for fpath in renames:
        fpath_out = os.path.join(dest_dir, renames[fpath])
        try:
            out_subdir = os.path.split(fpath_out)[0]
            if not os.path.exists(out_subdir):
                os.makedirs(out_subdir, exist_ok=True)
            shutil.copy2(fpath, fpath_out)  # try to preserve metadata
            all_created.append(fpath_out)
        except IOError:
            print(f"Failed to copy {fpath} to {fpath_out}")
            traceback.print_stack()
            fail_cnt += 1

    all_created.sort()
    print(f"\nCreated {len(all_created)} file(s):")
    for f in all_created:
        print(f)

    print(f"\nSuccessfully renamed {len(renames) - fail_cnt}/{len(all_slps)} slp files.")



