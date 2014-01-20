# photolib

manage your photo archive

- import new photos, generate date-based hierarchy

- analyze photos and metainformation (faces detected by [picasa](http://picasa.google.com/))

    - generate smaller photos (aka tiles, 240x240px) for mosaic rendering

    - generate closeup of detected faces

- render mosaic using [metapixel](http://www.complang.tuwien.ac.at/schani/metapixel/)

- generate html gallery of given photos, using [pandoc](http://johnmacfarlane.net/pandoc/) and [reveal.js](http://lab.hakim.se/reveal-js/)


## tl;dr

### install

download project, install prerequisites (ubuntu-specific)

```bash
git clone https://github.com/arnehilmann/photolib.git

cd photolib

bootstrap/ubuntu.sh
```

### usage

```bash
source ve/bin/activate  # activate photolib

transfer-photos --source-dir <BUNCH_OF_NEW_PHOTOS> --photos-dir <MY_PHOTO_LIBRARY>

# picasa face detection in MY_PHOTO_LIBRARY happens here

analyze-photos --photos-dir <MY_PHOTO_LIBRARY> --faces-dir <FACES_LIBRARY> --tiles-dir <TILES_LIBRARY>

prepare-mosaic --tiles-dir <TILES_LIBRARY>

render-mosaic --in <INPUT_FILE> --tiles-dir <TILES_LIBRARY>

generate-gallery <NAME_OF_GALLERY> <PHOTOS...>
```

## TODO

- add minimal exif data for photos without exif

- handle non-photos gracefully (movies, etc)

- integrate better with picasa (for face detection)

- integrate better with digikam

- store face data in xmp format (with bounding box)

