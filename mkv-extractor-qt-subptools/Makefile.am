bin_PROGRAMS = \
  subptools \
  subp2pgm

subptools_SOURCES = \
  subptools.c

subptools_LDADD = \
  $(LIBXML_LIBS) -lm

subp2pgm_SOURCES = \
  subp2pgm.c \
  vobsub.c   \
  spudec.c

subp2pgm_LDADD = \
  $(LIBPNG_LIBS) \
  $(LIBTIFF_LIBS) -lm

AM_CPPFLAGS = \
  $(LIBXML_CFLAGS) \
  $(LIBPNG_CFLAGS)

man_MANS = \
  subptools.1 \
  subp2pgm.1

install-exec-hook:
if HAVE_PNG_SUPPORT
	@rm -f $(DESTDIR)$(bindir)/subp2png
	$(LN_S) subp2pgm $(DESTDIR)$(bindir)/subp2png
endif
if HAVE_TIFF_SUPPORT
	@rm -f $(DESTDIR)$(bindir)/subp2tiff
	$(LN_S) subp2pgm $(DESTDIR)$(bindir)/subp2tiff
endif

EXTRA_DIST =  \
  vobsub.h \
  spudec.h \
  $(man_MANS)

CLEANFILES = *~ *.bak

