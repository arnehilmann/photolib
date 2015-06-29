# photolib

## How to install picasa3.9 on ubuntu

**fast-lane, without picasaweb-integration**

* get and install the last (and old) official picasa version for ubuntu:

```google
https://www.google.com/search?q=%22picasa+3.0%22+download+ubuntu
```

```bash
sudo dpkg -i Downloads/picasa-3.0*.deb
```

* get and copy-over the last official (non-ubuntu) version of picasa

```google
https://www.google.com/search?q="picasa+3.9"+download
```

```bash
wine Downloads/picasa39-setup.exe
sudo cp -r .wine/drive_c/Program\ Files\ \(x86\)/Google/Picasa3/* /opt/google/picasa/3.0/wine/drive_c/Program\ Files/Google/Picasa3
```
