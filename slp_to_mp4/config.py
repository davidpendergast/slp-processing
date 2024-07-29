import os, json
import shutil
import psutil


def check_path(path):
    if not os.path.exists(path):
        raise RuntimeError("{} does not exist".format(path))


class Config:

    def __init__(self, path_to_config):
        with open(path_to_config, 'r') as f:
            j = json.loads(f.read())

            self.path_to_melee_iso = os.path.expanduser(j['path_to_melee_iso'])
            self.path_to_dolphin_exe = os.path.expanduser(j['path_to_dolphin_exe'])
            self.ffmpeg = os.path.expanduser(shutil.which(j['ffmpeg']))

            check_path(self.path_to_melee_iso)
            check_path(self.path_to_dolphin_exe)
            check_path(self.ffmpeg)

            self.resolution = j['resolution']
            self.widescreen = j['widescreen']
            self.bitrateKbps = j['bitrateKbps']
            self.parallel_games = _calc_num_processes(j['parallel_games'])
            self.extra_frames = j['extra_frames']


def _calc_num_processes(val):
    if val == "recommended":
        return psutil.cpu_count(logical=False)
    else:
        return int(val)