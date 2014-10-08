bin_PROGRAMS = \
  subptools \
  subp2tiff

subptools_SOURCES = \
  subptools.c

subptools_LDADD = \
  $(LIBXML_LIBS) -lm

subp2tiff_SOURCES = \
  subp2pgm.c \
  vobsub.c   \
  spudec.c

subp2tiff_LDADD = \
  $(LIBPNG_LIBS) \
  $(LIBTIFF_LIBS) -lm

AM_CPPFLAGS = \
  $(LIBXML_CFLAGS) \
  $(LIBPNG_CFLAGS)

man_MANS = \
  subptools.1 \
  subp2tiff.1

EXTRA_DIST =  \
  vobsub.h \
  spudec.h \
  $(man_MANS)

CLEANFILES = *~ *.bak

