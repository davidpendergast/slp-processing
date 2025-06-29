import argparse
import os
import sys
import tempfile
import shutil
import traceback
import typing
from functools import total_ordering

# need newer (unpublished) version of py_slippi, for skip_frames option.
import py_slippi.slippi as slippi  # py_slippi, parsing library for slp files

import slp_to_mp4.slp2mp4 as slp2mp4

import utils


@total_ordering
class MeleeSet:

    def __init__(self, name, filepaths):
        self.name = name
        self.filepaths = filepaths

        self._parsed_metadata = None

    def get_output_filename(self):
        # remove special chars and such
        safe_string = "".join(c for c in self.name if c.isalpha()
                              or c.isdigit()
                              or c in ' _()').strip()
        return f"{safe_string}.mp4"

    def get_metadata(self) -> typing.Sequence[slippi.Game]:
        if self._parsed_metadata is None:
            res = []
            for fpath in self.filepaths:
                try:
                    game = slippi.Game(fpath, skip_frames=True)
                    res.append(game)
                except IOError:
                    print(f"ERROR: failed to parse SLP in set \"{self.name}\": {fpath}")
                    traceback.print_exc()
            self._parsed_metadata = tuple(res)
        return self._parsed_metadata

    def get_game_durations_frames(self, conf: slp2mp4.Config) -> typing.List[int]:
        res = []
        for game in self.get_metadata():
            res.append(game.metadata.duration)
            if conf is not None:
                res[-1] += conf.extra_frames
        return res

    def get_total_duration_frames(self, conf: slp2mp4.Config = None) -> int:
        return sum(self.get_game_durations_frames(conf=conf))

    def get_game_durations_ms(self, conf: slp2mp4.Config = None) -> typing.List[int]:
        return list(map(lambda x: int(x / 60 * 1000), self.get_game_durations_frames(conf=conf)))

    def get_total_duration_ms(self, conf: slp2mp4.Config = None) -> int:
        return sum(self.get_game_durations_ms(conf=conf))

    def get_approx_processing_time_ms(self, conf: slp2mp4.Config = None):
        if conf is None:
            return 0
        else:
            total = 0
            durations = self.get_game_durations_ms(conf=conf)
            nproc = conf.parallel_games
            for chunk in (durations[pos:pos + nproc] for pos in range(0, len(durations), nproc)):
                total += max(chunk)
            return total

    def get_approx_filesize_mb(self, conf: slp2mp4.Config = None):
        mb_per_ms = 0
        if conf is None:
            mb_per_ms = 0
        elif conf.bitrateKbps == 16000 and conf.resolution == '720p':
            mb_per_ms = 0.00195126157  # determined empirically

        duration_ms = self.get_total_duration_ms(conf=conf)
        return int(mb_per_ms * duration_ms)

    def __lt__(self, other: 'MeleeSet'):
        # sort by filenames, which should begin with timestamps
        my_filenames = list(map(lambda fpath: os.path.split(fpath)[1], self.filepaths))
        other_filenames = list(map(lambda fpath: os.path.split(fpath)[1], other.filepaths))
        return my_filenames < other_filenames


def parse_spec_file(fpath) -> typing.List[MeleeSet]:
    res = []
    with open(fpath) as file:
        cur_name = None
        cur_files = []
        for line in file:
            line = line.strip()
            if len(line) == 0:
                if cur_name is not None and len(cur_files) > 0:
                    res.append(MeleeSet(cur_name, cur_files))
                cur_name = None
                cur_files = []
            elif cur_name is None:
                cur_name = line.strip()
                cur_files = []
            else:
                # should be a path to a slp file
                if line.startswith("\""):
                    line = line[1:]
                if line.endswith("\""):
                    line = line[:-1]
                if not os.path.exists(line):
                    raise ValueError(f"File for set \"{cur_name}\" doesn't exist: {line}")
                if line.endswith(".slp"):
                    cur_files.append(line)
                else:
                    print(f"Ignoring non-slp file for set \"{cur_name}\": {line}")

    if cur_name is not None and len(cur_files) > 0:
        res.append(MeleeSet(cur_name, cur_files))

    return res


if __name__ == "__main__":
    parser = argparse.ArgumentParser("slp video creator")
    parser.add_argument("-spec", help="text file containing the list of sets", type=str)
    parser.add_argument("-dest", help="directory to write the mp4s", type=str)
    parser.add_argument("-nosort", action='store_true', help="flag that prevents slps from being sorted by timestamp within sets")

    args = parser.parse_args()
    specfile = args.spec
    if args.dest is not None:
        dest_dir = args.dest
    else:
        dest_dir = os.path.join(os.path.split(specfile)[0], "videos")
    print(f"\nWelcome to SLP Video Creator\n  spec file: {specfile}\n  output directory: {dest_dir}")

    conf = slp2mp4.Config('my_config.json' if os.path.exists('my_config.json') else 'config.json')

    total_processing_time_ms = 0
    total_video_duration_ms = 0
    total_filesize_mb = 0

    vids = parse_spec_file(specfile)
    print(f"\nFound {len(vids)} set(s) with {sum([len(v.filepaths) for v in vids])} total SLP(s):")
    for v in vids:
        processing_time_ms = v.get_approx_processing_time_ms(conf=conf)
        set_duration_ms = v.get_total_duration_ms(conf=conf)
        filesize_mb = v.get_approx_filesize_mb(conf=conf)

        total_processing_time_ms += processing_time_ms
        total_video_duration_ms += set_duration_ms
        total_filesize_mb += filesize_mb

        print(f"  {v.name} ({len(v.filepaths)} games, {utils.ms_to_timestamp(set_duration_ms)}, {filesize_mb} MB)")
        for fname in v.filepaths:
            print(f"    {fname}")

    print(f"\n{len(vids)} set(s) with {sum([len(v.filepaths) for v in vids])} total SLP(s)")
    print(f"Total duration: {utils.ms_to_timestamp(total_video_duration_ms)}")
    print(f"Estimated disk space needed: {total_filesize_mb / 1000:.1f} GB")
    print(f"Estimated Processing time: {utils.ms_to_timestamp(total_processing_time_ms)}")

    if not utils.ask_yes_or_no_question("Create videos?"):
        raise SystemExit

    fails = []
    for v in vids:
        try:
            if args.nosort:
                all_filepaths = list(v.filepaths)
            else:
                # sort by filename which should start with the timestamp
                all_filepaths = sorted(v.filepaths, key=lambda x: os.path.split(x)[1])

            outfile = os.path.join(dest_dir, v.get_output_filename())
            slp2mp4.record_and_combine_slps(conf, all_filepaths, outfile)

            if os.path.exists(outfile):
                bytesize = os.path.getsize(outfile)
                print(f"  Created {outfile} successfully ({int(bytesize / 1e6)} MB)")
            else:
                raise ValueError(f"Didn't throw an error, but failed to create {outfile}")
        except Exception as e:
            print(f"ERROR failed to create video for set: {v.name}")
            fails.append(v)
            traceback.print_exc()

    if len(fails) > 0:
        newline = '\n'
        print(f"\nFailed to process {len(fails)} set(s):\n"
              f"{newline.join([v.name for v in fails])}")
    else:
        print(f"\nSuccessfully processed all {len(vids)} set(s)")


