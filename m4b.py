#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# This file is in the Public Domain.
# Copyright (C) 2010 Benjamin Elbers <elbersb@gmail.com>
#
# Takes all mp3 files in the current directory and creates a properly tagged
# audio book (m4b) with chapter marks in the "output" directory.
#
# Note: The mp3 files should have proper ID3 tags. The "title" tag of each mp3
#       file is used as the corresponding chapter title. The "artist" and
#       "album" tags of the first file are used as tags for the complete
#       audio book.
# Note: To have the chapters in the correct order, the filenames have to be
#       sortable (e.g. "01 - First chapter.mp3", "02 - Second chapter.mp3").
# Note: To make the chapter marks show up on the iPod use gtkPod>=v0.99.14 or
#       iTunes for transferring the audio book.
#
# Requires: ffmpeg, MP4Box, mp4chaps, mutagen, libmad, mp3wrap
#  pip3 install --global-option=build_ext --global-option="-I/opt/homebrew/include/" --global-option="-L/opt/homebrew/lib" pymad


from mutagen.easyid3 import EasyID3

from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

import sox
import time
import os
import shutil
import subprocess
import sys
import tempfile
import logging
import unicodedata
import argparse
import re

# brew install ffmpeg mp3wrap mad gpac

OUTPUT_DIR = "./"
OUTPUT_TREE = False
COVER      = ''
mp3_files  = ''
AUTHOR     = ''
TITLE      = ''
ALBUM      = ''
SERIES     = ''
NARRATORS  = ''
DEBUG      = ''
TEMP       = tempfile.mkdtemp();
TFILE      = ''
BITRATE    = '128k'
Version    = '0.5.0'
COMMENT    = ''
SPEAKER    = ''
SERIES     = ''
LOGLEVEL   = logging.WARNING
MOVE     = False
RENAME   = False
DRYRUN   = False
INPUT_DIR = './'
FNULL = open(os.devnull, 'w')
filename   = ''
mp3stmp = []
DIR=''


def secs_to_hms(seconds):
    h, m, s, ms = 0, 0, 0, 0
    if "." in str(seconds):
        splitted = str(seconds).split(".")
        seconds = int(splitted[0])
        ms = int(splitted[1])
    m,s = divmod(seconds,60)
    h,m = divmod(m,60)
    ms = str(ms)
    try:
        ms = ms[0:3]
    except:
        pass
    return "%.2i:%.2i:%.2i.%s" % (h, m, s, ms)

def mkpath(tags):
    logging.debug(f"Creating directory name by tags")

    if '\xa9ART' not in tags:
        print("Please set Author")
        os.exit(99)

    author = tags['\xa9ART'][0]

    if '\xa9nam' not in tags:
        print("Please set Name")
        os.exit(99)
    name = tags['\xa9nam'][0]

    series = ''
    if "tvsh" in tags and tags['tvsh']:
        series = tags['tvsh'][0]

    album = ''
    if "\xa9alb" in tags and tags['\xa9alb']:
        album = tags['\xa9alb'][0]
    else:
        album = name

    speaker = ''
    if '\xa9wrt' in tags and tags['\xa9wrt']:
        speaker=tags['\xa9wrt'][0]

    comment = ''
    if '\xa9cmt' in tags and tags['\xa9cmt']:
        comment=tags['\xa9cmt'][0]

    logging.debug(f"Title:   {name}")
    logging.debug(f"album:   {album}")
    logging.debug(f"Series:  {series}")
    logging.debug(f"Speaker: {speaker}")
    logging.debug(f"Comment: {comment}")

    if album and series and album == name:
        #cut series from name
        k = re.compile( "%s.? (.+)" % (series) )
        pname=name
        if k.match(name):
            pname = k.search( str(name) ).group(1)
        logging.debug("Dir [album and series, album == title]: %s/%s/%s" % (author, series, pname ))
        DIR= "%s/%s/%s" % (author, series, pname )

    elif album and series and album != name:
        #cut series from name
        # k = re.compile( "%s.? (.+)" % (series) )
        # pname=name
        # if k.match(name):
        #     pname = k.search( str(name) ).group(1)
        logging.debug("Dir [album and series, album != title]: %s/%s/%s" % (author, series, album ))
        DIR= "%s/%s/%s" % (author, series, album )

    elif album and not series:
        logging.debug("Dir [album and not series]: %s/%s" % (author, album ))
        DIR= "%s/%s" % (author, album )

    elif series and not ALBUM:
        # Cut series name from File name
        k = re.compile( "%s.? (.+)" % (series) )
        pname=name
        if k.match(name):
            pname = k.search( str(name) ).group(1)
        DIR= "%s/%s/%s" % (author, series, pname )
    else:
        DIR= "%s/%s" % (author, pname )
    logging.debug(f"Path   : {DIR}")
    return DIR

def mkfilename(tags):
    logging.debug(f"Creating file name by tags")

    if '\xa9ART' not in tags:
        print("Please set Author")
        os.exit(99)

    author = tags['\xa9ART'][0]

    if '\xa9nam' not in tags:
        print("Please set Name")
        os.exit(99)
    name = tags['\xa9nam'][0]

    series = ''
    if "tvsh" in tags and tags['tvsh']:
        series = tags['tvsh'][0]

    album = ''
    if "\xa9alb" in tags and tags['\xa9alb']:
        album = tags['\xa9alb'][0]
    else:
        album = name

    speaker = ''
    if '\xa9wrt' in tags and tags['\xa9wrt']:
        speaker=tags['\xa9wrt'][0]

    comment = ''
    if '\xa9cmt' in tags and tags['\xa9cmt']:
        comment=tags['\xa9cmt'][0]

    logging.debug(f"Title:   {name}")
    logging.debug(f"album:   {album}")
    logging.debug(f"Series:  {series}")
    logging.debug(f"Speaker: {speaker}")
    logging.debug(f"Comment: {comment}")

    # Making new file name

    if name != album:
        k = re.compile( "%s. (.+)" % (album) )
        pname=name
        if k.match(name):
            pname = k.search( str(name) ).group(1)
        name = "%s - %s" % (album, pname)
    if series:
        k = re.compile( "%s.? (.+)" % (series) )
        pname=name
        if k.match(name):
            pname = k.search( str(name) ).group(1)
        filename =  "%s - %s. %s" % (author, series, pname)
    else:
        filename =  "%s - %s" % (author, name)
    if speaker:
        filename = filename + " [%s]" % (speaker)
    if comment:
        filename = filename + " (%s)" % (comment)
    filename=filename+".m4b"
    logging.debug(f"Filename: {filename}")

    return filename


print("mp3 to m4b converter by Andrii Petrenko (apl@petrenko.me)")

parser = argparse.ArgumentParser(
        prog='2m4b',
        description='mp3 to m4b converter by Andrii Petrenko (apl@petrenko.me)',
        epilog='-=*=-')


parser.add_argument('-A', '--album',   dest="album",   help="Audiobook album name")
parser.add_argument('-a', '--author',  dest="author",  help='Audiobook Author' )
parser.add_argument('-C', '--comment', dest="comment", help="Audiobook Comment")
parser.add_argument('-c', '--cover',   dest="cover",   help="Audiobook cover ")
parser.add_argument('-o', '--output',  dest="output",  help="destination directory for file output")
parser.add_argument('-S', '--series',  dest="series",  help="Audiobook Series")
parser.add_argument('-s', '--speaker', dest="speaker", help="Audiobook Speaker/Narrover")
parser.add_argument('-t', '--title',   dest="title",   help="Audiobook Title")
parser.add_argument('-m', '--move',    dest='move',    action='store_true', help='Move file to the proper directoy structure')
parser.add_argument('-d',              dest='dryrun',  action='store_true', help='DryRun action. Do not change anythiing')
parser.add_argument('-v', '--verbose', dest="verbose", action='store_true', help="verbose output")
parser.add_argument(      '--debug',   dest='debug' ,  action='store_true', help='Debug output')
parser.add_argument('filenames', type=str, nargs='+', help='Audiobook filenames',)

args = parser.parse_args()


DRYRUN     = args.dryrun
VERBOSE    = logging.INFO  if args.verbose        else LOGLEVEL
LOGLEVEL   = logging.DEBUG if args.debug          else LOGLEVEL
COVER      = args.cover    if args.cover          else COVER
AUTHOR     = args.author   if args.author         else AUTHOR
ALBUM      = args.album    if args.album          else ALBUM
TITLE      = args.title    if args.title          else TITLE
COMMENT    = args.comment  if args.comment        else COMMENT
COMMENT    = ''            if args.comment == '-' else COMMENT
SERIES     = args.series   if args.series         else SERIES
SPEAKER    = args.speaker  if args.speaker        else SPEAKER
SPEAKER    = ''            if args.speaker == '-' else SPEAKER
OUTPUT_DIR = args.output   if args.output         else OUTPUT_DIR
MOVE       = args.move
FILENAMES  = args.filenames

logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=LOGLEVEL)

if os.path.isdir(FILENAMES[0]) and len(FILENAMES) == 1:
    #We got single  directory
    INPUT_DIR  = args.filenames[0]
    print(INPUT_DIR)
    FILENAMES = []
    mp3_files = [filename for filename in os.listdir(INPUT_DIR+"/") if filename.endswith(".mp3") or filename.endswith(".MP3")]
    mp3_files.sort()
    for i in mp3_files:
        FILENAMES.append(INPUT_DIR+"/"+i)
    msg=f"Wrapping files from {INPUT_DIR}: "+ str(", " .join(FILENAMES))
    logging.debug(msg)
    logging.debug ("mp3wrap -v " +TEMP+ "/output.mp3 " + " ".join(FILENAMES) )
    subprocess.call(["mp3wrap"] + ["-v"] + [TEMP+"/output.mp3"] + FILENAMES, stdout=FNULL)

elif os.path.isfile(FILENAMES[0]) and len(FILENAMES) == 1:
    #single file, lets speedup
    logging.debug( f"Single file -- just copy {args.filenames[0]} to {TEMP}/output_MP3WRAP.mp3")
    shutil.copy (args.filenames[0], f"{TEMP}/output_MP3WRAP.mp3")

elif len(FILENAMES) > 255:
    # too many mp3 files
    logging.error("mp3wrap accept only less than 255 files")
    sys.exit(2)

else:
    #regular files
    msg=f"Wrapping files from {INPUT_DIR}: "+ str(", " .join(FILENAMES))
    logging.debug(msg)
    logging.debug ("mp3wrap -v " +TEMP+ "/output.mp3 " + " ".join(FILENAMES) )
    subprocess.call(["mp3wrap"] + ["-v"] + [TEMP+"/output.mp3"] + FILENAMES, stdout=FNULL)

logging.warning("Wrapping mp3 files complete")


# checking cover if exist
COVER = args.cover
if args.cover and not os.path.isfile(COVER):
    logging.error("Cover (" + COVER + ") does not exist")
    sys.exit(2)
elif not args.cover:
    COVER = INPUT_DIR+"/cover.jpg"  if os.path.isfile(INPUT_DIR+"/cover.jpg" ) else ''
    COVER = INPUT_DIR+"/Cover.jpg"  if os.path.isfile(INPUT_DIR+"/Cover.jpg" ) else ''
    COVER = INPUT_DIR+"/folder.jpg" if os.path.isfile(INPUT_DIR+"/folder.jpg") else ''
    COVER = INPUT_DIR+"/Folder.jpg" if os.path.isfile(INPUT_DIR+"/Folder.jpg") else ''
    COVER = INPUT_DIR+"/front.jpg"  if os.path.isfile(INPUT_DIR+"/front.jpg" ) else ''
    COVER = INPUT_DIR+"/Front.jpg"  if os.path.isfile(INPUT_DIR+"/Front.jpg" ) else ''
    COVER = INPUT_DIR+"/cover.png"  if os.path.isfile(INPUT_DIR+"/cover.png" ) else ''
    COVER = INPUT_DIR+"/Cover.png"  if os.path.isfile(INPUT_DIR+"/Cover.png" ) else ''
    COVER = INPUT_DIR+"/folder.png" if os.path.isfile(INPUT_DIR+"/folder.png") else ''
    COVER = INPUT_DIR+"/Folder.png" if os.path.isfile(INPUT_DIR+"/Folder.png") else ''
    COVER = INPUT_DIR+"/front.png"  if os.path.isfile(INPUT_DIR+"/front.png" ) else ''
    COVER = INPUT_DIR+"/Front.png"  if os.path.isfile(INPUT_DIR+"/Front.png" ) else ''

    if not COVER:
        logging.debug("trying to get Cover from 1st mp3 file")
        if LOGLEVEL == logging.DEBUG:
            # temporary subprocess.call(["ffmpeg"] + ["-i"] + [FILENAMES[0]] + [TEMP+"/cover.png"])
            subprocess.call(["ffmpeg"] + ["-i"] + [FILENAMES[0]] + [TEMP+"/cover.png"])
        else:
            subprocess.call(["ffmpeg"] + ["-i"] + [FILENAMES[0]] + [TEMP+"/cover.png"], stdout=FNULL, stderr=FNULL)
        if os.path.isfile(TEMP+"/cover.png"):
            COVER = TEMP+"/cover.png"

logging.debug("Cover file is: " + COVER )
logging.debug("Temporary directory is " + TEMP)


#debug ("Input *.mp3 file list is " + ",".join(mp3_files));
logging.warning("Converting " + ",".join(FILENAMES)+" to audiobook")

# wrap mp3
#todo: do not do that if dryrun ??
# if len(args.filenames) == 1:


# create chapters file
chapters_file = open(TEMP+'/chapters', 'w')
counter = 0
time    = 0

for filename in FILENAMES:
    audio = MP3(filename, ID3=EasyID3)
    length = sox.file_info.duration(filename) # don't use mutagen here, because it isn't very precise
    logging.debug(f"File {filename} length is {length} sec")
    logging.debug(audio.pprint())
    if audio.info.bitrate   >= 160000:
        BITRATE = '160k'
    elif audio.info.bitrate >= 128000:
        BITRATE = '128k'
    elif audio.info.bitrate >= 96000:
        BITRATE = '96k'
    else:
        BITRATE = '64k'

    logging.debug(f"File {filename} bitrate is {BITRATE}")

    if not TITLE:
        try:
            TITLE = audio["album"][0]
        except:
            pass

    if not TITLE:
        try:
            TITLE = audio["title"][0]
        except:
            pass

        logging.debug(f"File {filename} Title is {TITLE}")

    if not AUTHOR:
        try:
            AUTHOR = audio["artist"][0]
        except:
            pass

    logging.debug(f"File {filename} Author is {AUTHOR}")

    if TFILE:
        title = os.path.splitext(os.path.basename(filename))[0]
    else:
        try:
            title = audio["title"][0]
            if len(title) > 90:
                title = title[:90]
        except:
            title = os.path.splitext(os.path.basename(filename))[0]

    logging.debug(f"File {filename} chapter name is {title}")

    counter += 1
    chapters_file.write("CHAPTER%i=%s\n" % (counter, secs_to_hms(time)))
    chapters_file.write("CHAPTER%iNAME=%s\n" % (counter, title))
    logging.debug( "Chapter: " +str(counter)+", length: " +str(length)+ ", Title: " + title )
    time += length

chapters_file.close()

if not AUTHOR:
    logging.error("Please set Author")
    sys.exit(99)


# convert to aac
ffmpeg = 'ffmpeg -i '+TEMP+'/output_MP3WRAP.mp3 -y -vn -acodec libfdk_aac -ab '+BITRATE+' -ar 44100 -f mp4 -threads 8 '+TEMP+'/output.aac'
logging.debug(ffmpeg)
if LOGLEVEL == logging.DEBUG:
    subprocess.call(ffmpeg.split(" "))
else:
    subprocess.call(ffmpeg.split(" "), stdout=FNULL, stderr=FNULL)

if not ALBUM:
    ALBUM = TITLE

# add chapters
logging.debug("Adding Chapters")
if LOGLEVEL == logging.DEBUG:
    subprocess.call(["MP4Box", "-add", TEMP+"/output.aac", "-chap", TEMP+"/chapters", TEMP+"/output.mp4"])
else:
    subprocess.call(["MP4Box", "-add", TEMP+"/output.aac", "-chap", TEMP+"/chapters", TEMP+"/output.mp4"], stdout=FNULL, stderr=FNULL)

# convert chapters to quicktime format
logging.debug ("converting to the Quicktime Format")
if LOGLEVEL == logging.DEBUG:
    subprocess.call(["mp4chaps", "--convert", "--chapter-qt", TEMP+"/output.mp4"])
else:
    subprocess.call(["mp4chaps", "--convert", "--chapter-qt", TEMP+"/output.mp4"], stdout=FNULL)

# create tags, rename file
logging.debug("Adding tags")

logging.debug(f"TITLE   : {TITLE}")
logging.debug(f"ALBUM   : {ALBUM}")
logging.debug(f"AUTHOR  : {AUTHOR}")
logging.debug(f"COMMENT : {COMMENT}")
logging.debug(f"SPEAKER : {SPEAKER}")
logging.debug(f"SERIES  :  {SERIES}")

# create tags, rename file
audio = MP4(TEMP+"/output.mp4")
audio["\xa9nam"] = [TITLE]
audio["\xa9alb"] = [ALBUM]
audio["\xa9ART"] = [AUTHOR]
audio["\xa9cmt"] = [COMMENT]
audio['\xa9wrt'] = [SPEAKER]
audio['aART']    = [SPEAKER]
audio['tvsh']    = [SERIES]

tags=audio.tags

audio.save()

if COVER:
    if LOGLEVEL == logging.DEBUG:
        logging.debug("Adding Cover is: "+COVER)
        subprocess.call(["mp4art", "--add", COVER, TEMP+"/output.mp4"])
    else:
        subprocess.call(["mp4art", "--add", COVER, TEMP+"/output.mp4"], stdout=FNULL)

newfile=mkfilename(tags)
newpath=mkpath(tags)


if MOVE:
    DIR=f"{OUTPUT_DIR}/{newpath}"
else:
    DIR=f"{OUTPUT_DIR}"

logging.debug(f"Saving Audiobook to {DIR}/{newfile}")
logging.debug(f"Creating directory {DIR}")
if not os.path.isdir(f"{DIR}"):
    try:
        logging.debug("Creating directory {DIR}")
        os.makedirs(f"{DIR}")
    except OSError as error:
        print(error)
        sys.exit("99")

logging.debug(f"Move {TEMP}/output.mp4 to {DIR}/{newfile}" )

shutil.move(f"{TEMP}/output.mp4", f"{DIR}/{newfile}")

print(f"Please check result:{DIR}/{newfile}")

if INPUT_DIR != "./":
    shutil.move (INPUT_DIR, INPUT_DIR+".Done")

# cleanup

if LOGLEVEL == logging.DEBUG:
    logging.debug("see temp directory: "+TEMP)
    sys.exit()
else:
    os.remove(TEMP+"/chapters")
    os.remove(TEMP+"/output.aac")
    os.remove(TEMP+"/output_MP3WRAP.mp3")
    if os.path.isfile(TEMP+"/cover.png"):
        os.remove(TEMP+"/cover.png")
    os.removedirs(TEMP)

FNULL.close()
