#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

#AC_PREREQ([2.69])
AC_INIT([subptools], [1.0.0])
AC_CONFIG_SRCDIR([spudec.c])
AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE()

# Checks for programs.
AC_PROG_CC

# Check for libs
PKG_CHECK_MODULES(LIBXML, "libxml-2.0")
AC_SUBST(LIBXML_CFLAGS)
AC_SUBST(LIBXML_LIBS)

PKG_CHECK_MODULES(LIBPNG, "libpng zlib", [have_png_support=yes], [have_png_support=no])
AC_SUBST(LIBPNG_CFLAGS)
AC_SUBST(LIBPNG_LIBS)

if test x"$have_png_support" = x"yes"; then
  AC_DEFINE(HAVE_PNG_SUPPORT, 1, [Define to 1 if png is supported.])
fi

AM_CONDITIONAL(HAVE_PNG_SUPPORT, [test x"$have_png_support" = x"yes"])

AC_CHECK_LIB([m], [sqrt], [], [exit 1])

AC_CHECK_LIB([tiff], [TIFFOpen], [LIBTIFF_LIBS="-ltiff" && have_tiff_support=yes], [have_tiff_support=no])
AC_SUBST(LIBTIFF_LIBS)

if test x"$have_tiff_support" = x"yes"; then
  AC_DEFINE(HAVE_TIFF_SUPPORT, 1, [Define to 1 if tiff is supported.])
fi

AM_CONDITIONAL(HAVE_TIFF_SUPPORT, [test x"$have_tiff_support" = x"yes"])

AC_PROG_LN_S

# Checks for header files.
AC_CHECK_HEADERS([fcntl.h inttypes.h limits.h netinet/in.h stddef.h stdlib.h string.h unistd.h])

# Checks for typedefs, structures, and compiler characteristics.
AC_C_INLINE
AC_TYPE_OFF_T
AC_TYPE_SIZE_T
AC_TYPE_SSIZE_T
AC_TYPE_UINT16_T
AC_TYPE_UINT32_T
AC_TYPE_UINT8_T
AC_CHECK_TYPES([ptrdiff_t])

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_REALLOC
AC_CHECK_FUNCS([dup2 floor memmove memset rint strcasecmp strchr strdup strerror strncasecmp strrchr strtol strtoul])

AC_CONFIG_FILES([Makefile])
AC_OUTPUT
