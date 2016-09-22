import os
import logging
import shutil
import subprocess
import sys
import tempfile

from photolib import match_any_tiles_suffices

TILE_SIZE = 240
TABLES_MXT = "tables.mxt"


class Preparer(object):
    def __init__(self, tiles_dir):
        self.tiles_dir = tiles_dir

    def main(self):
        for dirpath, dirnames, filenames in os.walk(self.tiles_dir):
            dirnames.sort()
            filenames = filter(match_any_tiles_suffices, filenames)
            if not filenames:
                continue
            # logging.info("%s: preparing..." % dirpath)
            tmpdir = tempfile.mkdtemp()

            tables_mxt = os.path.join(dirpath, TABLES_MXT)
            if os.path.exists(tables_mxt):
                tables_mxt_mtime = os.path.getmtime(tables_mxt)
            else:
                tables_mxt_mtime = 0

            uptodate = True
            for filename in filenames:
                sys.stdout.write(".")
                filename_mtime = os.path.getmtime(os.path.join(dirpath, filename))
                if filename_mtime > tables_mxt_mtime:
                    uptodate = False
                    break
            sys.stdout.flush()
            if os.path.getmtime(dirpath) > tables_mxt_mtime:
                uptodate = False

            if uptodate:
                # logging.info("%s: uptodate, skipping..." % dirpath)
                continue
            logging.info("%s: generating %s" % (dirpath, TABLES_MXT))

            if os.path.exists(tables_mxt):
                os.remove(tables_mxt)
            with open(os.devnull, 'w') as devnull:
                subprocess.call(["metapixel-prepare",
                                 "--width=%i" % TILE_SIZE,
                                 "--height=%i" % TILE_SIZE,
                                 dirpath,
                                 tmpdir], stdout=devnull)
            with open(tables_mxt, "w") as new_tables_mxt:
                with open(os.path.join(tmpdir, TABLES_MXT)) as tmp_tables_mxt:
                    for line in tmp_tables_mxt:
                        new_tables_mxt.write(line.replace('.png"', '"'))
            shutil.rmtree(tmpdir)
