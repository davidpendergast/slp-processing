import os, json
import shutil
import psutil


def check_path(name, path):
    if path.startswith("SET THIS TO"):
        raise RuntimeError(f"Please edit config.json and set a path for: {name}")
    if not os.path.exists(path):
        raise RuntimeError(f"config.json's {name} path does not exist: {path}")


class Config:

    def __init__(self, path_to_config):
        with open(path_to_config, 'r') as f:
            j = json.loads(f.read())

            self.path_to_melee_iso = os.path.expanduser(j['path_to_melee_iso'])
            self.path_to_dolphin_exe = os.path.expanduser(j['path_to_dolphin_exe'])
            self.ffmpeg = os.path.expanduser(shutil.which(j['ffmpeg']))

            check_path('path_to_melee_iso', self.path_to_melee_iso)
            check_path('path_to_dolphin_exe', self.path_to_dolphin_exe)
            check_path('ffmpeg', self.ffmpeg)

            self.resolution = j['resolution']
            self.widescreen = j['widescreen']
            self.bitrateKbps = j['bitrateKbps']
            self.parallel_games = _calc_num_processes(j['parallel_games'])
            self.extra_frames = j['extra_frames']

            # Hard limit on render time per slp file.
            # Somewhat dangerous to enable, because if the rendering runs slowly
            # (due to system RAM overuse), it will cause the game to cutoff early.
            # But having no limit may allow the processing to become stuck?
            # Unclear why that might occur.
            # TODO Should come up with a better way to detect & report freezes
            self.max_render_time_per_slp_secs = 30 * 60


def _calc_num_processes(val):
    if val == "recommended":
        return psutil.cpu_count(logical=False)
    else:
        return int(val)