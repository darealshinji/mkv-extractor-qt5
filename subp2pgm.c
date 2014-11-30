/*
 * Copyright (C) 2002, 2003 Jan Panteltje <panteltje@yahoo.com>,
 *
 * Modified by Zachary Brewster-Geisz, 2003, to work on big-endian
 * machines.
 *
 * Modified by Henry Mason, 2003, to use both PNG and BMP, and to use
 * the dvdauthor submux format.
 *
 * Modified and copy right Jan Panteltje 2002
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * With many changes by Scott Smith (trckjunky@users.sourceforge.net)
 *
 * With many changes by Olivier Rolland (billl@users.sourceforge.net)
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
 * USA
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <getopt.h>
#include <limits.h>

#include <netinet/in.h>

#ifdef HAVE_PNG_SUPPORT
#include <png.h>
#include <zlib.h>
#endif

#ifdef HAVE_TIFF_SUPPORT
#include <tiffio.h>
#endif

#include "vobsub.h"
#include "spudec.h"

#define FALSE 0
#define TRUE (!FALSE)

#define CBUFSIZE 65536
#define PSBUFSIZE 10

enum
{
  FORMAT_PPM,
#ifdef HAVE_PNG_SUPPORT
  FORMAT_PNG,
#endif
#ifdef HAVE_TIFF_SUPPORT
  FORMAT_TIFF
#endif
};

unsigned int vobsub_id = 0;

static unsigned int expand = 0;
static unsigned int width = 720;
static unsigned int height = 576;
static unsigned int normalize = 0;

static int debug, forced, format;
static unsigned int subno;
static char *output;

FILE *xml_file;
void *spudec;

static int
write_ppm (char *file_name, int x0, int y0, int w, int h, unsigned char *src, unsigned char *srca, int stride)
{
  FILE *f;
  unsigned int x, y;

  f = fopen (file_name, "w");

  fprintf (f, "P5\n" "%d %d\n" "255\n", w, h);

  for (y = 0; y < h; y++)
  {
    for (x = 0; x < w; x++)
    {
      int res;

      if (srca[x])
        res = src[x] * (256 - srca[x]);
      else
        res = 0;
      
      res = (65535 - res) >> 8;

      putc (res & 0xff, f);
    }

    src += stride;
    srca += stride;
  }

  putc ('\n', f);

  fclose (f);

  return 0;
}

#ifdef HAVE_PNG_SUPPORT
static int
write_png (char *file_name, int x0, int y0, int w, int h, unsigned char *src, unsigned char *srca, int stride)
{
  png_structp png_ptr;
  png_infop info_ptr;
  FILE *fp;

  fp = fopen (file_name, "wb");
  if (!fp)
  {
    fprintf (stderr, "** ERROR: Unable to open/create file %s\n", file_name);
    return -1;
  }

  png_ptr = png_create_write_struct (PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);

  if (!png_ptr)
    return -1;

  info_ptr = png_create_info_struct (png_ptr);
  if (!info_ptr)
  {
    png_destroy_write_struct (&png_ptr, (png_infopp) NULL);
    return -1;
  }

  if (setjmp (png_jmpbuf(png_ptr)))
  {
    png_destroy_write_struct (&png_ptr, &info_ptr);
    fclose (fp);
    return -1;
  }

  png_init_io (png_ptr, fp);

  /* turn on or off filtering, and/or choose specific filters */
  png_set_filter (png_ptr, 0, PNG_FILTER_NONE);

  /* set the zlib compression level */
  png_set_compression_level (png_ptr, Z_BEST_COMPRESSION);

  /* set other zlib parameters */
  png_set_compression_mem_level (png_ptr, 8);
  png_set_compression_strategy (png_ptr, Z_DEFAULT_STRATEGY);
  png_set_compression_window_bits (png_ptr, 15);
  png_set_compression_method (png_ptr, 8);

  if (expand)
    png_set_IHDR (png_ptr, info_ptr, width, height,
        8, PNG_COLOR_TYPE_RGB_ALPHA, PNG_INTERLACE_NONE,
        PNG_COMPRESSION_TYPE_DEFAULT,
        PNG_FILTER_TYPE_DEFAULT);
  else
    png_set_IHDR (png_ptr, info_ptr, w, h,
        8, PNG_COLOR_TYPE_RGB_ALPHA, PNG_INTERLACE_NONE,
        PNG_COMPRESSION_TYPE_DEFAULT,
        PNG_FILTER_TYPE_DEFAULT);

  png_write_info (png_ptr, info_ptr);

  png_set_packing (png_ptr);

  if (src != NULL)
  {
    unsigned int x, y;
    png_bytep out_buf, temp;

    temp = out_buf = malloc (w * h * 4 * sizeof (png_byte));

    for (y = 0; y < h; y ++)
    {
      for (x = 0; x < w; x ++)
      {
        const png_byte pixel =  src[x];
        const png_byte alpha = srca[x];

        *temp++ = 255 - pixel;
        *temp++ = 255 - pixel;
        *temp++ = 255 - pixel;
        *temp++ = alpha ? 255 : 0;
      }

      src += stride;
      srca += stride;
    }

    if (expand)
    {
      png_bytep image;

      temp = out_buf;
      image = malloc (width * height * 4 * sizeof (png_byte));
      memset (image, 0, width * height * 4 * sizeof (png_byte));

      for (y = y0; y < y0 + h; y ++)
      {
        png_bytep to = &image[y * width * 4 + x0 * 4];

        for (x = 0; x < w; x ++)
        {
          *to++ = *temp++;
          *to++ = *temp++;
          *to++ = *temp++;
          *to++ = *temp++;
        }
      }

      w = width;
      h = height;

      free (out_buf);
      out_buf = image;
    }

    {
      png_bytep row_pointers[h];

      for (y = 0; y < h; y++)
        row_pointers[y] = out_buf + y * w * 4;

      png_write_image (png_ptr, row_pointers);
    }

    png_write_end (png_ptr, info_ptr);
    free (out_buf);
  }

  png_destroy_write_struct (&png_ptr, &info_ptr);

  fclose(fp);

  return 0;
}
#endif

#ifdef HAVE_TIFF_SUPPORT
static int
write_tiff (char *file_name, int x0, int y0, int w, int h, unsigned char *src, unsigned char *srca, int stride)
{
  TIFF *out;
  unsigned int x, y;
  unsigned char *buf;
  uint16_t compression = COMPRESSION_NONE; /* COMPRESSION_CCITTFAX3 */
  uint32_t g3opts = 0;

  out = TIFFOpen (file_name, "w");

  TIFFSetField (out, TIFFTAG_IMAGEWIDTH, (uint32_t) w);
  TIFFSetField (out, TIFFTAG_IMAGELENGTH, (uint32_t) h);
  TIFFSetField (out, TIFFTAG_ORIENTATION, ORIENTATION_TOPLEFT);
  TIFFSetField (out, TIFFTAG_SAMPLESPERPIXEL, 1);
  TIFFSetField (out, TIFFTAG_BITSPERSAMPLE, 8);
  TIFFSetField (out, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
  TIFFSetField (out, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);
  TIFFSetField (out, TIFFTAG_COMPRESSION, compression);

  if (compression == COMPRESSION_CCITTFAX3)
  {
/*
    g3opts = GROUP3OPT_2DENCODING;
    g3opts |= GROUP3OPT_FILLBITS;
*/
    TIFFSetField (out, TIFFTAG_GROUP3OPTIONS, g3opts);
  }

  TIFFSetField (out, TIFFTAG_ROWSPERSTRIP, TIFFDefaultStripSize (out, (uint32_t) -1));

  if (TIFFScanlineSize (out) > w)
    buf = (unsigned char *)_TIFFmalloc (w);
  else
    buf = (unsigned char *)_TIFFmalloc (TIFFScanlineSize(out));

  for (y = 0; y < h; y++)
  {
    for (x = 0; x < w; x++)
    {
      int res;

      if (srca[x])
        res = src[x] * (256 - srca[x]);
      else
        res = 0;
      
      res = (65535 - res) >> 8;

      buf[x] = res & 0xff;
    }

    src += stride;
    srca += stride;

    if (TIFFWriteScanline (out, buf, y, 0) < 0)
      break;
  }

  if (buf)
     _TIFFfree (buf);

  TIFFClose (out);

  return 0;
}
#endif

static void
write_pts (char *preamble, unsigned int pts)
{
  unsigned int temp, h, m, s, ms;

  temp = pts;
  temp /= 90;
  h = temp / 3600000;
  temp %= 3600000;
  m = temp / 60000;
  temp %= 60000;
  s = temp / 1000;
  temp %= 1000;
  ms = temp;

  fprintf (xml_file, "%s=\"%02u:%02u:%02u.%03u\"", preamble, h, m, s, ms);
}

void
write_spu (int x0, int y0, int w, int h, unsigned char* src, unsigned char *srca, int stride)
{
  unsigned int start_pts, end_pts;
  char buf[256];

  if ((!forced || spudec_forced (spudec)) && w > 0 && h > 0)
  {
    subno ++;

    fprintf (xml_file, "  <subtitle id=\"%d\" ", subno);

    switch (format)
    {
#ifdef HAVE_PNG_SUPPORT
      case FORMAT_PNG:
        sprintf (buf, "%s%04d.png", output, subno);
        write_png (buf, x0, y0, w, h, src, srca, stride);
        break;
#endif
#ifdef HAVE_TIFF_SUPPORT
      case FORMAT_TIFF:
        sprintf (buf, "%s%04d.tif", output, subno);
        write_tiff (buf, x0, y0, w, h, src, srca, stride);
        break;
#endif
      default:
        sprintf (buf, "%s%04d.pgm", output, subno);
        write_ppm (buf, x0, y0, w, h, src, srca, stride);
        break;
    }

    spudec_get_pts (spudec, &start_pts, &end_pts);
    write_pts ("start", start_pts);
    if (end_pts > start_pts && end_pts != UINT_MAX)
    {
      fprintf (xml_file, " ");
      write_pts ("stop", end_pts);
    }

    fprintf (xml_file, ">\n");

    fprintf (xml_file, "    <image>%s</image>\n", buf);
    fprintf (xml_file, "  </subtitle>\n");
  }
}

static void
load_palette (char *palet_file, unsigned int *palette)
{
  FILE *file;
  int n, c;

  file = fopen (palet_file, "r");
  if (file != NULL)
  {
    for (n = 0; n < 16; n++)
    {
      if (fscanf (file, "%d", &c) != 1)
      {
        fprintf (stderr, "** ERROR: Unable to get palette information from file '%s'\n", palet_file);
        break;
      }

      /* YUV */
      palette[n] = c;

      if (debug > 3)
        fprintf (stderr, "pal: %d #%d\n", n, palette[n]);
    }
    fclose (file);
  }
  else
  {
    palet_file[0] = 0;
    fprintf (stderr, "** WARNING: Unable to open %s, using defaults\n", palet_file);
  }
}

static void
parse_expand (const char *optarg)
{
  unsigned int w, h;

  expand = 1;

  if (optarg)
  {
    if (sscanf (optarg, "%ux%u", &w, &h) != 2)
      fprintf (stderr, "** WARNING: Unable to parse %s, using defaults\n", optarg);
    else
    {
      width = w;
      height = h;
    }
  }
}

static void
usage (const char *name)
{
  fprintf (stdout, "Usage:\n");
  fprintf (stdout, "  %s [OPTION...] <vobsub basename>\n", name);
  fprintf (stdout, "\n");
  fprintf (stdout, "Help Options:\n");
  fprintf (stdout, "  -h, --help                  Show help options\n");
  fprintf (stdout, "\n");
  fprintf (stdout, "Application Options:\n");
  fprintf (stdout, "  -o, --output=<basename>     Use basename for output (default: vobsub basename)\n");
  fprintf (stderr, "  -p, --palette=<filename>    The palette file (default: none)\n");
  fprintf (stderr, "  -s, --sid=<sid>             The subtitle id (default: 0)\n");
  fprintf (stderr, "  -e, --expand[=<w>x<h>]      Expand the subtitle to the given resolution\n");
  fprintf (stderr, "                              (default: don't expand or expand to 720x576\n");
  fprintf (stderr, "  -f, --forced                Extract only forced subtitles\n");
  fprintf (stderr, "  -n, --normalize             Normalize the palette\n");
  fprintf (stderr, "  -v, --verbose               Increase verbosity level\n");
  fprintf (stdout, "\n");
}

static const char *shortopts = "hfnvs:o:p:e::";
static const struct option longopts[] =
{
  { "help",      no_argument,       NULL, 'h' },
  { "forced",    no_argument,       NULL, 'f' },
  { "normalize", no_argument,       NULL, 'n' },
  { "verbose",   no_argument,       NULL, 'v' },
  { "expand",    optional_argument, NULL, 'e' },
  { "sid",       required_argument, NULL, 's' },
  { "output",    required_argument, NULL, 'o' },
  { "palette",   required_argument, NULL, 'p' },
  { NULL,        0,                 NULL,  0  }
};

int
main (int argc, char **argv)
{
  int option, packet_len, pts100;
  void *vobsub, *packet_data;

  char *palet_file = NULL;

  char filename[FILENAME_MAX];

#ifdef HAVE_PNG_SUPPORT
  if (strcmp (argv[0], "subp2png") == 0)
    format = FORMAT_PNG;
#endif
#ifdef HAVE_TIFF_SUPPORT
  if (strcmp (argv[0], "subp2tiff") == 0)
    format = FORMAT_TIFF;
#endif

  while ((option = getopt_long (argc, argv, shortopts, longopts, NULL)) != EOF)
  {
    switch (option)
    {
      case 's':
        vobsub_id = atoi (optarg);
        break;
      case 'o':
        output = optarg;
        break;
      case 'p':
        palet_file = optarg;
        break;
      case 'f':
        forced = 1;
        break;
      case 'v':
        debug ++;
        break;
      case 'n':
        normalize = 1;
        break;
      case 'e':
        parse_expand (optarg);
        break;
      case 'h':
        usage (argv[0]);
        return EXIT_SUCCESS;
        break;
      default:
        fprintf (stderr, "** ERROR: Unknown option. Use -h to list all valid options.\n");
        return EXIT_FAILURE;
        break;
    }
  }

  if (optind >= argc)
  {
    usage (argv[0]);
    return EXIT_FAILURE;
  }

  if (!output)
    output = argv[optind];

  if (strlen (output) > FILENAME_MAX)
  {
    fprintf (stderr, "** ERROR: Error max length of base for filename creation is %d characters\n", FILENAME_MAX);
    return EXIT_FAILURE;
  }

  sprintf (filename, "%s.xml", output);
  xml_file = fopen (filename, "w+");
  if (!xml_file)
  {
    fprintf (stderr, "** ERROR: Cannot open file %s\n", filename);
    return EXIT_FAILURE;
  }

  vobsub = vobsub_open (argv[optind], NULL, 0, &spudec);
  if (!vobsub)
  {
    fclose (xml_file);
    fprintf (stderr, "** ERROR: Cannot open VobSub\n");
    return EXIT_FAILURE;
  }

  if (palet_file)
  {
    unsigned int palette[16];

    load_palette (palet_file, palette);
    spudec_update_palette (spudec, palette);
  }

  spudec_set_forced_subs_only (spudec, forced);
  spudec_set_normalize_palette (spudec, normalize);

  fprintf (xml_file, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
  fprintf (xml_file, "<subtitles>\n");

  while ((packet_len = vobsub_get_next_packet (vobsub, &packet_data, &pts100)) >= 0)
  {
    spudec_assemble (spudec, packet_data, packet_len, pts100);
    spudec_update (spudec, write_spu);
  }

  fprintf (xml_file, "</subtitles>\n");
  fclose (xml_file);

  vobsub_close (vobsub);
  spudec_free (spudec);

  fprintf (stdout, "%u files generated\n", subno);

  return EXIT_SUCCESS;
}

