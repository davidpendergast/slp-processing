#!/usr/bin/env python3
import os, shutil, uuid, multiprocessing, tempfile, traceback
from slippi import Game
from slp_to_mp4.config import Config
from slp_to_mp4.dolphinrunner import DolphinRunner
from slp_to_mp4.ffmpegrunner import FfmpegRunner

# Heavily modified version of https://github.com/NunoDasNeves/slp-to-mp4
# This version is a utility library and cannot be run as a top-level script.


def record_slp(conf: Config, slp_file, outfile):
    """Converts a single slp file to an mp4.
    :param conf: Configuration settings.
    :param slp_file: filepath of the slp.
    :param outfile: mp4 filepath to create.
    """
    # Parse file with py-slippi to determine number of frames
    slippi_game = Game(slp_file)
    num_frames = slippi_game.metadata.duration + conf.extra_frames

    dolphin_dir = os.path.split(conf.path_to_dolphin_exe)[0]
    dolphin_user_dir = os.path.join(dolphin_dir, 'User')

    workingdir = tempfile.mkdtemp("dolphin_workingdir")

    try:
        # Dump frames
        with DolphinRunner(conf, dolphin_user_dir, workingdir, uuid.uuid4()) as dolphin_runner:
            video_file, audio_file = dolphin_runner.run(slp_file, num_frames)

            # Encode
            ffmpeg_runner = FfmpegRunner(conf.ffmpeg)
            ffmpeg_runner.run(video_file, audio_file, outfile)

            print('Created {}'.format(outfile))
    finally:
        _try_to_cleanup_tempdir(workingdir)


def combine_mp4s(conf: Config, mp4list, outfile):
    """Combines a list of mp4 filepaths to a single mp4 using ffmpeg.
    :param conf: Configuration settings.
    :param mp4list: list of mp4 filepaths, note these should all live in the same directory.
    :param outfile: mp4 filepath to create.
    """
    if len(mp4list) == 0:
        raise ValueError("mp4list is empty")

    tempdir = tempfile.mkdtemp()
    concat_fpath = os.path.join(tempdir, "concat_file.txt")
    try:
        lines = []
        for f in mp4list:
            if not os.path.exists(f):
                raise ValueError(f"Cannot combine mp4 because it doesn't exist: {f}")
            if not f.endswith('.mp4'):
                raise ValueError(f"Cannot combine non-mp4 file: {f}")
            lines.append("file \'" + f + "\'" + "\n")

        with open(concat_fpath, 'w+') as concat_file:
            concat_file.writelines(lines)

        ffmpeg_runner = FfmpegRunner(conf.ffmpeg)
        ffmpeg_runner.combine(concat_fpath, outfile)
    finally:
        _try_to_cleanup_tempdir(tempdir)

    if not os.path.exists(outfile):
        raise ValueError(f"Failed to create: {outfile}")


def record_and_combine_slps(conf: Config, slpfiles, outfile):
    """Converts a list of slp files to a single mp4.
    :param conf: Configuration settings.
    :param slpfiles: List of slp filepaths to record and combine.
    :param outfile: Output mp4 filepath to create.
    """
    if len(slpfiles) == 0:
        raise ValueError(f"No slp files provided for outfile={outfile}")

    tempdir = tempfile.mkdtemp(prefix='slp2mp4_out')
    try:
        mproc_args = []
        created_mp4s = []
        for idx, slp_file in enumerate(slpfiles):
            mp4_file = os.path.join(tempdir, f"game{idx+1}.mp4")
            mproc_args.append((conf, slp_file, mp4_file))
            created_mp4s.append(mp4_file)

        pool = multiprocessing.Pool(processes=conf.parallel_games)
        pool.starmap(record_slp, mproc_args)
        pool.close()

        combine_mp4s(conf, created_mp4s, outfile)
    finally:
        _try_to_cleanup_tempdir(tempdir)


def _try_to_cleanup_tempdir(tempdir):
    try:
        shutil.rmtree(tempdir)
    except IOError:
        print(f"ERROR failed to clean up temp directory: {tempdir}")
        traceback.print_exc()