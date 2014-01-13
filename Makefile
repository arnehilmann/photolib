.SECONDARY:

OUTDIR = out
SOURCE = $(OUTDIR)/gallery.md
TARGET = $(OUTDIR)/gallery.html
REVEAL_HOME = $(HOME)/dev/reveal.js


$(TARGET):	$(SOURCE) gallery/*.css 
	rm -rf $(OUTDIR)
	mkdir -p $(OUTDIR)
	mkdir -p $(OUTDIR)/reveal.js/
	cp -r $(REVEAL_HOME)/js $(REVEAL_HOME)/lib $(REVEAL_HOME)/css $(OUTDIR)/reveal.js/
	cp -r gallery/* $(OUTDIR)
	pandoc --slide-level 1 -V transition=linear -V backgroundTransition=fade -i -s --mathjax -i -t revealjs --template my --data-dir $(OUTDIR) --css photolib.css $(SOURCE) -o $(TARGET)

clean:
	rm -rf $(OUTDIR) $(TARGET)

