import os
import logging
import shutil
import subprocess
import tempfile

TILE_SIZE = 240
TABLES_MXT = "tables.mxt"

class Preparer(object):
    def __init__(self, tiles_dir):
        self.tiles_dir = tiles_dir

    def main(self):
        for dirpath, dirnames, filenames in os.walk(self.tiles_dir):
            dirnames.sort()
            if not filenames:
                continue
            tmpdir = tempfile.mkdtemp()
            logging.info("%s: preparing" % dirpath)
            tables_mxt = os.path.join(dirpath, TABLES_MXT)
            if os.path.exists(tables_mxt):
                os.remove(tables_mxt)
            with open(os.devnull, 'w') as devnull:
                subprocess.call(["metapixel-prepare", "--width=%i" % TILE_SIZE, "--height=%i" % TILE_SIZE, dirpath, tmpdir], stdout=devnull)
            with open(tables_mxt, "w") as new_tables_mxt:
                with open(os.path.join(tmpdir, TABLES_MXT)) as tmp_tables_mxt:
                    for line in tmp_tables_mxt:
                        new_tables_mxt.write(line.replace('.png"', '"'))
            shutil.rmtree(tmpdir)
