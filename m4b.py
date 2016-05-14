#!/usr/bin/env python
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

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

import mad
import time
import os
import subprocess
import sys
import getopt
import datetime
import tempfile

# brew install ffmpeg mp3wrap mad gpac

OUTPUT_DIR = "./output"
COVER      = ''
mp3_files  = ''
AUTHOR     = ''
TITLE      = ''
DEBUG      = ''
TEMP       = tempfile.mkdtemp();
TFILE      = ''
Version    = '0.1.0'

argv = sys.argv[1:]

def debug(msg):
    if DEBUG :
        today = datetime.datetime.today()
        print today.strftime('%Y-%m-%dT%H:%M:%S.%f')+" [" + sys.argv[0] + "] " + msg

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

print "mp3 to m4b converter by Andrii Petrenko (apl@petrenko.me)"

try:
    opts, args = getopt.getopt(argv,"hi:c:a:t:df",["ifile=","cover=","author=","title="])
except getopt.GetoptError:
    print 'm4b.py [-i <inputfile>[,<inputfile2>...]] [-c <cover>] [-a <author>] [-t <title>] -d -h'
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print 'm4b.py [-i <inputfile>[,<inputfile2>...]] [-c <cover>] [-a <author>] [-t <title>] -d -h'
        sys.exit()
    elif opt == '-d':
        DEBUG=1
    elif opt in ("-i", "--ifile"):
        mp3_files = arg.split(',')
    elif opt in ("-c", "--cover"):
        COVER = arg
        if not os.path.isfile(COVER):
            print "Cover (" + COVER + ") does not exist"
            sys.exit(2)
        debug("Cover file is " + COVER )
    elif opt in ("-a", "--author"):
        AUTHOR = arg.decode('utf-8')
    elif opt in ("-t", "--title"):
        TITLE = arg.decode('utf-8')
    elif opt in ("-f", "--file"):
        TFILE = 'true'

debug("Temporary directory is " + TEMP)

# # output dir
# if not os.path.isfile("output"):
#     os.mkdir("output")

# get mp3
if not mp3_files :
    mp3_files = [filename for filename in os.listdir(".") if filename.endswith(".mp3")]
    mp3_files.sort()

#debug ("Input *.mp3 file list is " + ",".join(mp3_files));
print "Converting " + ",".join(mp3_files)+" to audiobook"

FNULL = open(os.devnull, 'w')
# wrap mp3
debug ("mp3wrap -v " +TEMP+ "/output.mp3" + ",".join(mp3_files) )
subprocess.call(["mp3wrap"] + ["-v"] + [TEMP+"/output.mp3"] + mp3_files, stdout=FNULL)

# convert to aac
ffmpeg = 'ffmpeg -i '+TEMP+'/output_MP3WRAP.mp3 -y -vn -acodec libfaac -ab 128k -ar 44100 -f mp4 -threads 4 '+TEMP+'/output.aac'
debug(ffmpeg)
subprocess.call(ffmpeg.split(" "), stdout=FNULL, stderr=FNULL)

# create chapters file
chapters_file = open(TEMP+'/chapters', 'w')
counter = 0
time    = 0

for filename in mp3_files:
    audio = MP3(filename, ID3=EasyID3)
    length = mad.MadFile(filename).total_time() / 1000. # don't use mutagen here, because it isn't very precise

    if not TITLE:
        try:
            TITLE = audio["album"][0]
        except:
            pass

    if not AUTHOR:
        try:
            AUTHOR = audio["artist"][0]
        except:
            pass

    if TFILE:
        title = filename.decode('utf-8')
    else:
        try:
            title = audio["title"][0]
        except:
            title = filename.decode('utf-8')

    counter += 1

    chapters_file.write("CHAPTER%i=%s\n" % (counter, secs_to_hms(time)))
    chapters_file.write("CHAPTER%iNAME=%s\n" % (counter, title.encode('utf-8')))
    debug( "Chapter: " +str(counter)+", length: " +str(length)+ ", Title: " +title.encode('utf-8') )

    time += length

chapters_file.close()

# add chapters

subprocess.call(["MP4Box", "-add", TEMP+"/output.aac", "-chap", TEMP+"/chapters", TEMP+"/output.mp4"], stdout=FNULL, stderr=FNULL)

# convert chapters to quicktime format
subprocess.call(["MP4chaps", "--convert", "--chapter-qt", TEMP+"/output.mp4"], stdout=FNULL)

# create tags, rename file
audio = MP4(TEMP+"/output.mp4")
audio["\xa9nam"] = [TITLE]
audio["\xa9alb"] = [TITLE]
audio["\xa9ART"] = [AUTHOR]
audio.save()

if not COVER:
    if os.path.isfile("cover.jpg"):
        COVER = "cover.jpg"
else
    subprocess.call(["mp4art", "--add", COVER, TEMP+"/output.mp4"], stdout=FNULL)

debug("Rename "+TEMP+"/output.mp4 " +AUTHOR+" - "+TITLE+".m4b" )
os.rename(TEMP+"/output.mp4", "%s - %s.m4b" % (AUTHOR, TITLE))

# cleanup
os.remove(TEMP+"/chapters")
os.remove(TEMP+"/output.aac")
os.remove(TEMP+"/output_MP3WRAP.mp3")
os.removedirs(TEMP)
FNULL.close()

# last report
print "Please check result: %s - %s.m4b" % (AUTHOR, TITLE)
# print
# print "Now use iTunes or gtkPod>=v0.99.14 to transfer the audio book to your iPod."
# print
