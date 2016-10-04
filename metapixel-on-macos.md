# How to compile 10year old metapixel sources on a rather new MacOS

Unpacking and compiling the metapixel source code, you get an
"error: incomplete definition of type 'struct png_info_def'".

Problem is, that metapixel usen deep references in libpng-internal data structures.
libpng1.4 was a transition release, deprecating some of these references;
since libpng1.5 such access results in an error as described above.

So you need an older version of libpng:

```
shell$  brew install homebrew/versions/libpng12
```

Put these in your Makefile:
```
MACOS_CCOPTS = -I/usr/local/opt/libpng12/include
MACOS_LDOPTS = -L/usr/local/opt/libpng12/lib
```

then you can ```make``` the executables; put them somewhere in your ```PATH```.
