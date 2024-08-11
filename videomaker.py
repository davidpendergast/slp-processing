import argparse
import os
import tempfile
import shutil
import traceback

import slp_to_mp4.slp2mp4 as slp2mp4

import utils


class MeleeSet:

    def __init__(self, name, filepaths):
        self.name = name
        self.filepaths = filepaths

    def get_output_filename(self):
        return f"{self.name}.mp4"  # TODO rm special chars and such


def parse_spec_file(fpath):
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
                # should be a path to an slp
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

    args = parser.parse_args()
    specfile = args.spec
    dest_dir = args.dest
    print(f"\nWelcome to SLP Video Creator\n  spec file: {specfile}\n  output directory: {dest_dir}")

    vids = parse_spec_file(specfile)
    print(f"\nFound {len(vids)} set(s) with {sum([len(v.filepaths) for v in vids])} total SLP(s):")
    for v in vids:
        print(f"  {v.name} ({len(v.filepaths)} games)")
        for fname in v.filepaths:
            print(f"    {fname}")

    if not utils.ask_yes_or_no_question("Create videos?"):
        raise SystemExit

    conf = slp2mp4.Config('my_config.json' if os.path.exists('my_config.json') else 'config.json')

    fails = []
    for v in vids:
        try:
            # sort by filename which should start with the timestamp
            sorted_filepaths = sorted(v.filepaths, key=lambda x: os.path.split(x)[1])

            outfile = os.path.join(dest_dir, v.get_output_filename())
            slp2mp4.record_and_combine_slps(conf, sorted_filepaths, outfile)

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









































