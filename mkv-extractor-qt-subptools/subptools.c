/* srttool-2 - Various manipulations of srtfiles
 * Copyright (C) 2002-2006 Arne Driescher <driescher@users.sf.net>
 * Copyright (C) 2006-2012 Olivier Rolland <billl@users.sourceforge.net>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <getopt.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <math.h>

#include <sys/types.h>
#include <sys/stat.h>

#include <libxml/xmlreader.h>

#define TRUE  1
#define FALSE 0

#define MAX_TEXT_LEN 4096

#define CR "\x0d"
#define LF "\x0a"

enum
{
  FORMAT_SUBP,
  FORMAT_SRT,
  FORMAT_SPUMUX
};

typedef struct
{
  unsigned int hour;
  unsigned int min;
  unsigned int sec;
  unsigned int msec;
} subp_time_t;

typedef struct
{
  unsigned int number;
  subp_time_t start_time;
  subp_time_t stop_time;
  char *image;
  char *text;
} subp_tag_t;

typedef struct
{
  int (* header) (FILE       *file);
  int (* footer) (FILE       *file);
  int (* tag)    (FILE       *file,
                  subp_tag_t *tag);
} subp_writer_t;

static unsigned int verbose;
static unsigned int renumber;
static unsigned int convert;
static unsigned int adjust;
static unsigned int subst;
static unsigned int strip;
static unsigned int help;
static char input_file[FILENAME_MAX];
static char output_file[FILENAME_MAX];
static double offset = 0.0;
static double factor = 1.0;

static unsigned int first_tag_number = 1;
static unsigned int last_tag_number = ~0;

static const char *newline = LF;

static subp_time_t adjustment;

static unsigned int
parse_shift (const char *value)
{
  if (sscanf (value, "%lf", &offset) != 1)
  {
    fprintf (stderr, "** ERROR: Invalid parameter for option -d\n");
    return -1;
  }

  if (verbose)
    fprintf (stderr, "** ERROR: Using time offset of %lf\n", offset);

  return 0;
}

static unsigned int
parse_cut (const char *value)
{
  if (sscanf (value, "%u,%u", &first_tag_number, &last_tag_number) == 0)
  {
    fprintf (stderr, "** ERROR: Invalid parameter for option -c\n");
    return -1;
  }

  if (first_tag_number == 0)
  {
    first_tag_number = 1;
    if (verbose)
      fprintf (stderr, "Setting first tag to 1\n");
  }

  if (verbose)
    fprintf (stderr, "Writing from %d to %d entries. \n", first_tag_number, last_tag_number);

  return 0;
}

static unsigned int
parse_adjust (const char *value)
{
  if (sscanf (value, "%u:%u:%u,%u", &adjustment.hour, 
        &adjustment.min, &adjustment.sec, &adjustment.msec) != 4)
  {
    fprintf (stderr, "** ERROR: Invalid parameter for option -a\n");
    return -1;
  }

  if (verbose)
    fprintf (stderr, "Adjusting to %02d:%02d:%02d,%.3d as start time\n",
        adjustment.hour, adjustment.min, adjustment.sec, adjustment.msec);

  adjust = TRUE;

  return TRUE;
}

static unsigned int
parse_expand (const char *value)
{
  double expansion;

  if (sscanf (value, "%lf", &expansion) != 1)
  {
    fprintf (stderr, "** ERROR: Invalid parameter for option -e\n");
    return -1;
  }

  /* calculate the resulting scaling factor */
  factor = (3600.0 + expansion) / 3600.0;

  if (verbose)
    fprintf (stderr, "Using %f seconds for hour expansion\n", expansion);

  return 0;
}

static int
parse_convert (const char *value)
{
  convert = -1;

  if (strcmp (value, "srt") == 0)
    convert = FORMAT_SRT;

  if (strcmp (value, "spumux") == 0)
    convert = FORMAT_SPUMUX;

  return convert;
}

static int
parse_newline (const char *value)
{
  if (strcmp (value, "cr") == 0 || strcmp (value, "CR") == 0)
  {
    newline = CR;
    return 0;
  }

  if (strcmp (value, "lf") == 0 || strcmp (value, "LF") == 0)
  {
    newline = LF;
    return 0;
  }

  if (strcmp (value, "cr+lf") == 0 || strcmp (value, "CR+LF") == 0)
  {
    newline = CR LF;
    return 0;
  }

  return -1;
}

static int
xml_read (xmlTextReader *reader, const char *name, xmlElementType type)
{
/*
  do
  {
*/
  if (xmlTextReaderRead (reader) < 0)
    return -1;
/*
  }
  while (xmlTextReaderIsEmptyElement (reader) == 1);
*/
  if (xmlTextReaderNodeType (reader) != type)
    return -1;

  if (name && !xmlStrEqual (xmlTextReaderConstName (reader), (xmlChar *) name))
    return -1;

  return 0;
}

static void
free_subp_tag (subp_tag_t *tag)
{
  if (tag->text)
    free (tag->text);

  if (tag->image)
    free (tag->image);

  memset (tag, 0, sizeof (subp_tag_t));
}

static int
read_subp_header (xmlTextReader *reader)
{
  if (xml_read (reader, "subtitles", XML_ELEMENT_NODE) < 0)
  {
    fprintf (stderr, "** ERROR: Cannot find subtitles node\n");
    return -1;
  }

  return 0;
}

static int
read_subp_footer (xmlTextReader *reader)
{
  if (!xmlStrEqual (xmlTextReaderConstName (reader), (xmlChar *) "subtitles"))
  {
    fprintf (stderr, "** ERROR: Cannot find subtitles ending node\n");
    return -1;
  }

  if (xmlTextReaderRead (reader) != 0)
    return -1;

  return 0;
}

static int
read_subp_tag (xmlTextReader *reader, subp_tag_t *tag)
{
  char *value;

  if (xml_read (reader, "subtitle", XML_ELEMENT_NODE) < 0)
  {
    if (!xmlStrEqual (xmlTextReaderConstName (reader), (xmlChar *) "subtitles"))
      fprintf (stderr, "** ERROR: Cannot find subtitle node\n");
    return -1;
  }

  value = (char *) xmlTextReaderGetAttribute (reader, (xmlChar *) "id");
  if (!value)
  {
    fprintf (stderr, "** ERROR: Cannot get id property\n");
    return -1;
  }

  /* read the current number */
  if (sscanf (value, "%u", &tag->number) != 1)
  {
    fprintf (stderr, "** ERROR: Cannot parse id property (%s)\n", strerror (errno));
    return -1;
  }

  free (value);

  value = (char *) xmlTextReaderGetAttribute (reader, (xmlChar *) "start");
  if (!value)
    return -1;

  if (sscanf (value, "%u:%u:%u.%u",
        &tag->start_time.hour, &tag->start_time.min, &tag->start_time.sec, &tag->start_time.msec) != 4)
    return -1;

  free (value);

  value = (char *) xmlTextReaderGetAttribute (reader, (xmlChar *) "stop");
  if (!value)
    tag->stop_time = tag->start_time;
  else if (sscanf (value, "%u:%u:%u.%u",
        &tag->stop_time.hour, &tag->stop_time.min, &tag->stop_time.sec, &tag->stop_time.msec) != 4)
    return -1;

  free (value);

  /* read the subtitle */
  if (xml_read (reader, NULL, XML_ELEMENT_NODE) < 0)
    return -1;

  if (xmlStrEqual (xmlTextReaderConstName (reader), (xmlChar *) "text"))
  {
    if (xml_read (reader, NULL, XML_TEXT_NODE) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot get text node for subtitle %d\n", tag->number);
      return -1;
    }

    tag->text = (char *) xmlTextReaderValue (reader);
    if (!tag->text)
    {
      fprintf (stderr, "** ERROR: Cannot get text content for subtitle %d\n", tag->number);
      return -1;
    }

    if (xml_read (reader, "text", XML_ELEMENT_DECL) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot get text ending node for subtitle %d\n", tag->number);
      return -1;
    }
  }
  else if (xmlStrEqual (xmlTextReaderConstName (reader), (xmlChar *) "image"))
  {
    if (xml_read (reader, NULL, XML_TEXT_NODE) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot get image node for subtitle %d\n", tag->number);
      return -1;
    }

    tag->image = (char *) xmlTextReaderValue (reader);
    if (!tag->image)
    {
      fprintf (stderr, "** ERROR: Cannot get image content for subtitle %d\n", tag->number);
      return -1;
    }

    if (xml_read (reader, "image", XML_ELEMENT_DECL) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot get image ending node for subtitle %d\n", tag->number);
      return -1;
    }
  }
  else
  {
    fprintf (stderr, "** ERROR: Cannot find text or image node for subtitle %d\n", tag->number);
    return -1;
  }

  if (xml_read (reader, "subtitle", XML_ELEMENT_DECL) < 0)
  {
    fprintf (stderr, "** ERROR: Cannot find subtitle ending node\n");
    return -1;
  }

  return 0;
}

static int
write_subp_header (FILE *file)
{
  if (fprintf (file, "<subtitles>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write subtitles node (%s)\n", strerror (errno));
    return -1;
  }

  return 0;
}

static int
write_subp_footer (FILE *file)
{
  if (fprintf (file, "</subtitles>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write subtitles ending node (%s)\n", strerror (errno));
    return -1;
  }

  return 0;
}

static int
write_subp_tag (FILE *file, subp_tag_t *tag)
{
  fprintf (file, "  <subtitle ");

  /* write the tag number */
  if (fprintf (file, "id=\"%u\"", tag->number) < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write tag number (%s)\n", strerror (errno));
    return -1;
  }

  fprintf (file, " ");

  /* write out the new time stamp */
  if (fprintf (file, "start=\"%02u:%02u:%02u.%03u\" stop=\"%02u:%02u:%02u.%03u\"",
      tag->start_time.hour, tag->start_time.min, tag->start_time.sec, tag->start_time.msec,
      tag->stop_time.hour, tag->stop_time.min, tag->stop_time.sec, tag->stop_time.msec) < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write time stamp (%s)\n", strerror (errno));
    return -1;
  }

  fprintf (file, ">\n");

  if (tag->text)
  {
    /* write out the subtitle */
    if (fprintf (file, "    <text>%s</text>\n", tag->text) < 0)
      return -1;
  }

  if (tag->image)
  {
    /* write out the filename */
    if (fprintf (file, "    <image>%s</image>\n", tag->image) < 0)
      return -1;
  }

  if (fprintf (file, "  </subtitle>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write subtitle ending node (%s)\n", strerror (errno));
    return -1;
  }

  return 0;
}

static int
write_srt_tag (FILE *file, subp_tag_t *tag)
{
  if (!tag->text)
    fprintf (stderr, "** WARNING: Cannot write text (not defined)\n");
  else
  {
    if (fprintf (file, "%d%s", tag->number, newline) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot write tag number (%s)\n", strerror (errno));
      return -1;
    }

    if (fprintf (file, "%02u:%02u:%02u,%03u --> %02u:%02u:%02u,%03u%s",
          tag->start_time.hour, tag->start_time.min, tag->start_time.sec, tag->start_time.msec,
          tag->stop_time.hour, tag->stop_time.min, tag->stop_time.sec, tag->stop_time.msec, newline) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot write time stamp (%s)\n", strerror (errno));
      return -1;
    }

    if (fprintf (file, "%s%s%s", tag->text, newline, newline) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot write text (%s)\n", strerror (errno));
      return -1;
    }
  }

  return 0;
}

static int
write_spumux_header (FILE *file)
{
  if (fprintf (file, "<subpictures>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write subpictures node (%s)\n", strerror (errno));
    return -1;
  }

  if (fprintf (file, "  <stream>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write stream node (%s)\n", strerror (errno));
    return -1;
  }

  return 0;
}

static int
write_spumux_footer (FILE *file)
{
  if (fprintf (file, "  </stream>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write stream ending node (%s)\n", strerror (errno));
    return -1;
  }

  if (fprintf (file, "</subpictures>\n") < 0)
  {
    fprintf (stderr, "** ERROR: Cannot write subpictures ending node (%s)\n", strerror (errno));
    return -1;
  }

  return 0;
}

static int
write_spumux_tag (FILE *file, subp_tag_t *tag)
{
  if (!tag->image)
    fprintf (stderr, "** WARNING: Cannot write spu node (no image)\n");
  else
  {
    if (fprintf (file, "    <spu image=\"%s\" start=\"%02u:%02u:%02u.%03u\" end=\"%02u:%02u:%02u.%03u\" />\n",
        tag->image, tag->start_time.hour, tag->start_time.min, tag->start_time.sec, tag->start_time.msec,
        tag->stop_time.hour, tag->stop_time.min, tag->stop_time.sec, tag->stop_time.msec) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot write spu node (%s)\n", strerror (errno));
      return -1;
    }
  }

  return 0;
}

static double
srt_time2sec (const subp_time_t *time_stamp)
{
  /* convert time stamp to seconds */
  return time_stamp->hour * 3600 + time_stamp->min * 60 +
    time_stamp->sec + time_stamp->msec / 1000.0;
}

static subp_time_t
sec2srt_time (double t)
{
  subp_time_t time_stamp;

  /* convert seconds to time stamp */
  time_stamp.hour = t / (3600);
  time_stamp.min = (t - 3600 * time_stamp.hour) / 60;
  time_stamp.sec = (t - 3600 * time_stamp.hour - 60 * time_stamp.min);
  time_stamp.msec = (unsigned int) rint ((t - 3600 * time_stamp.hour -
        60 * time_stamp.min - time_stamp.sec) * 1000.0);

  return time_stamp;
}

static void
adjust_subp_time (subp_time_t *time_stamp)
{
  double t;

  t = srt_time2sec (time_stamp);

  /*  adjust time according to offset */
  t += offset;

  /*  don't allow negative time */
  if (t < 0)
    t = 0;

  /*  scale the time */
  t *= factor;

  /*  writeout start and end time of this title */
  *time_stamp = sec2srt_time (t);
}

static char *
get_file_content (int fd)
{
  struct stat stat_buf;
  size_t bytes_read;
  char *buf;

  if (fstat (fd, &stat_buf) < 0)
  {
    close (fd);
    return NULL;
  }

  if (stat_buf.st_size <= 0 || !S_ISREG (stat_buf.st_mode))
  {
    close (fd);
    return NULL;
  }

  buf = (char *) malloc (stat_buf.st_size + 1);

  bytes_read = 0;
  while (bytes_read < stat_buf.st_size)
  {
    ssize_t rc;

    rc = read (fd, buf + bytes_read, stat_buf.st_size - bytes_read);

    if (rc < 0)
    {
      free (buf);
      return NULL;
    }
    else if (rc == 0)
      break;
    else
      bytes_read += rc;
  }
    
  buf[bytes_read] = '\0';

  while (--bytes_read)
  {
    if (isspace ((int) buf[bytes_read]))
      buf[bytes_read] = '\0';
    else
      break;
  }

  return buf;
}

static int
substitute_txt (subp_tag_t *tag)
{
  char filename[FILENAME_MAX];
  int fd;

  if (sscanf (tag->image, "%[^\r\n]", filename) != 1)
  {
    fprintf (stderr, "** ERROR: Cannot read substitution filename (%s)\n", strerror (errno));
    return -1;
  }
  strcat (filename, ".txt");

  if (verbose)
    fprintf (stderr, "** ERROR: Reading substitution from file '%s'\n", filename);

  fd = open (filename, O_RDONLY);
  if (fd < 0)
  {
    fprintf (stderr, "** ERROR: Cannot open file '%s' for substitution (%s)\n", filename, strerror (errno));
    return -1;
  }

  tag->text = get_file_content (fd);
  if (!tag->text)
  {
    close (fd);
    return -1;
  }

  free (tag->image);
  tag->image = NULL;

  close (fd);

  return 0;
}

static void
usage (const char *name)
{
  fprintf (stdout, "Usage:\n");
  fprintf (stdout, "  %s [OPTION...]\n", name);
  fprintf (stdout, "\n");
  fprintf (stdout, "Help Options:\n");
  fprintf (stdout, "  -h, --help                     Show help options\n");
  fprintf (stdout, "\n");
  fprintf (stdout, "Application Options:\n");
  fprintf (stdout, "  -v, --verbose                  Verbose\n");
  fprintf (stdout, "  -r, --renumber                 Renumber all entries\n");
  fprintf (stdout, "  -s, --subst                    Substitute filename after time stamps by its\n");
  fprintf (stdout, "                                 content\n");
  fprintf (stdout, "  -w, --strip                    Remove leading white space in text lines\n");
  fprintf (stdout, "  -d, --shift=<time>             Shift all timestamps by <time> seconds\n");
  fprintf (stdout, "  -c, --cut=<first[,last]>       Write only entries from first to last (default:\n");
  fprintf (stdout, "                                 all entries) to output\n");
  fprintf (stdout, "  -a, --adjust=<hh:mm:ss,ms>     Adjust all time stamps so that the first tag\n");
  fprintf (stdout, "                                 begins at hh:mm:ss,ms\n");
  fprintf (stdout, "  -e, --expand=<seconds>         Expand the subtitle hour by <seconds>\n");
  fprintf (stdout, "  -t, --convert=<format>         Convert the subtitle in the given format (srt,\n");
  fprintf (stdout, "                                 spumux)\n");
  fprintf (stdout, "  -n, --newline=<cr|lf|cr+lf>    Specifies the newline sequence (default: %s)\n", newline);
  fprintf (stdout, "  -i, --input=<filename>         Use filename for input (default: stdin)\n");
  fprintf (stdout, "  -o, --output=<filename>        Use filename for output (default: stdout)\n");
  fprintf (stdout, "\n");
}

static const char *shortopts = "hvrswd:c:a:e:t:i:o:n:";
static const struct option longopts[] =
{
  { "help",     no_argument,       NULL, 'h' },
  { "verbose",  no_argument,       NULL, 'v' },
  { "renumber", no_argument,       NULL, 'r' },
  { "subst",    no_argument,       NULL, 's' },
  { "strip",    no_argument,       NULL, 'w' },
  { "shift",    required_argument, NULL, 'd' }, 
  { "cut",      required_argument, NULL, 'c' },
  { "adjust",   required_argument, NULL, 'a' },
  { "expand",   required_argument, NULL, 'e' },
  { "convert",  required_argument, NULL, 't' },
  { "input",    required_argument, NULL, 'i' },
  { "output",   required_argument, NULL, 'o' },
  { "newline",  required_argument, NULL, 'n' },
  { NULL,       0,                 NULL, 0   }
};

static const subp_writer_t writer[] =
{
  { write_subp_header,   write_subp_footer,   write_subp_tag   },
  { NULL,                NULL,                write_srt_tag    },
  { write_spumux_header, write_spumux_footer, write_spumux_tag }
};

int
main (int argc, char *argv[])
{
  xmlTextReader *reader;
  subp_tag_t input_tag, output_tag;

  unsigned int input_counter, output_counter;
  int c, optidx;

  while ((c = getopt_long (argc, argv, shortopts, longopts, &optidx)) != EOF)
  {
    switch (c)
    {
      case 'h':
        help = TRUE;
        break;
      case 'v':
        verbose = TRUE;
        break;
      case 'r':
        renumber = TRUE;
        break;
      case 's':
        subst = TRUE;
        break;
      case 'w':
        strip = TRUE;
        break;
      case 'd':
        if (parse_shift (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 'c':
        if (parse_cut (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 'a':
        if (parse_adjust (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 'e':
        if (parse_expand (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 't':
        if (parse_convert (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 'n':
        if (parse_newline (optarg) < 0)
          return EXIT_FAILURE;
        break;
      case 'i':
        strncpy (input_file, optarg, FILENAME_MAX);
        break;
      case 'o':
        strncpy (output_file, optarg, FILENAME_MAX);
        break;
      default:
        /* TODO */
        return EXIT_FAILURE;
    }
  }

  if (help)
  {
    usage (argv[0]);
    return EXIT_SUCCESS;
  }

  if (strlen (input_file) > 0)
  {
    int fd;

    fd = open (input_file, O_RDONLY);
    if (fd < 0)
    {
      fprintf (stderr, "** ERROR: Cannot open file %s for reading (%s)\n", input_file, strerror (errno));
      return EXIT_FAILURE;
    }

    if (dup2 (fd, STDIN_FILENO) < 0)
    {
      fprintf (stderr, "** ERROR: Cannot ...\n");
      return EXIT_FAILURE;
    }

    if (verbose)
      fprintf (stderr, "Using %s for input\n", input_file);
  }

  if (strlen (output_file) > 0)
  {
    if (!freopen (output_file, "w", stdout))
    {
      fprintf (stderr, "** ERROR: Cannot open file %s for writing (%s)\n", input_file, strerror (errno));
      return EXIT_FAILURE;
    }

    if (verbose)
      fprintf (stderr, "Using %s for output\n", output_file);
  }

  input_counter = output_counter = 0;
  input_tag.text = output_tag.text = NULL;
  input_tag.image = output_tag.image = NULL;

  reader = xmlReaderForFd (STDIN_FILENO, NULL, NULL, 0);
  if (!reader)
  {
    fprintf (stderr, "** ERROR: Cannot open XML reader\n");
    return EXIT_FAILURE;
  }

  xmlTextReaderSetup (reader, NULL, NULL, NULL, XML_PARSE_NOBLANKS);

  if (read_subp_header (reader) < 0)
    return EXIT_FAILURE;

  if (writer[convert].header && (* writer[convert].header) (stdout) < 0)
    return EXIT_FAILURE;

  while (read_subp_tag (reader, &input_tag) == 0)
  {
    input_counter ++;

    /*  only handle tags in given input range */
    if (input_tag.number < first_tag_number ||
        input_tag.number > last_tag_number)
      continue;
    
    /*  copy the tag */
    output_tag = input_tag;
    if (input_tag.text)
      output_tag.text = strdup (input_tag.text);
    if (input_tag.image)
      output_tag.image = strdup (input_tag.image);

    free_subp_tag (&input_tag);

    /*  adjust tag number if -r option is given */
    if (renumber)
      output_tag.number = output_counter + 1;

    /*  adjust time so that tag starts at time given by -a option */
    if (adjust && output_counter == 0)
    {
      /*  simply add the correct adjustment to time_offset */
      offset += srt_time2sec (&adjustment) -
        srt_time2sec (&output_tag.start_time);
    }

    /*  add/sub the delay given in -d and -a option */
    /*  and scale the time line according to -e option */
    adjust_subp_time (&output_tag.start_time);
    adjust_subp_time (&output_tag.stop_time);

    if (subst)
    {
      /*  substitute the filename in next line by its content */
      substitute_txt (&output_tag);
    }

    /*  write out the tag */
    if (writer[convert].tag && (* writer[convert].tag) (stdout, &output_tag) < 0)
      return EXIT_FAILURE;
    free_subp_tag (&output_tag);

    output_counter ++;
  }

  if (read_subp_footer (reader) < 0)
    return EXIT_FAILURE;

  xmlFreeTextReader (reader);

  if (writer[convert].footer && (* writer[convert].footer) (stdout) < 0)
    return EXIT_FAILURE;
/*
  if (strlen (input_file) > 0)
    fclose (stdin);
*/
  if (strlen (output_file) > 0)
    fclose (stdout);

  return EXIT_SUCCESS;
}

