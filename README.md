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


## Referenced Projects/Applications

- [python](http://www.python.org/)

- [virtualenv](http://www.virtualenv.org/en/latest/)

- [jhead](http://www.sentex.net/~mwandel/jhead/)

- [exiftool](http://www.sno.phy.queensu.ca/~phil/exiftool/)

- [imagemagick](http://www.imagemagick.org/)

- [metapixel](http://www.complang.tuwien.ac.at/schani/metapixel/)

- [pandoc](http://johnmacfarlane.net/pandoc/)

- [reveal.js](http://lab.hakim.se/reveal-js/)


## How to install picasa3.9 on ubuntu

** fast-lane, without picasaweb-integration **

* get and install the last (and old) official picasa version for ubuntu:

```google
https://www.google.com/search?q=%22picasa+3.0%22+download
```

* get and copy-over the last official (non-ubuntu) version of picasa

```google
https://www.google.com/search?q="picasa+3.9"+download
```

```bash
wine Downloads/picasa39-setup.exe
sudo cp -r .wine/drive_c/Program\ Files\ \(x86\)/Google/Picasa3/* /opt/google/picasa/3.0/wine/drive_c/Program\ Files/Google/Picasa3
```


## TODO

- add minimal exif data for photos without exif

- integrate better with picasa (for face detection)

- integrate better with digikam (sync of metadata)

- store face data in metadata (with bounding box)

- support [pixelize](http://lashwhip.com/pixelize.html) for mosaic rendering

