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

OUTPUT_DIR = "./output"
COVER      = ''
mp3_files  = ''
AUTHOR     = ''
TITLE      = ''
DEBUG      = ''

argv = sys.argv[1:]

def debug(msg):
    if DEBUG :
        today = datetime.date.today()
        print today.strftime('%Y%m%dT%H%M%S')+" "+msg

try:
    opts, args = getopt.getopt(argv,"hi:c:a:t:d",["ifile=","cover=","author=","title="])
except getopt.GetoptError:
    print 'm4b.py [-i <inputfile>] [-c <cover>] [-a <author>] [-t <title>]'
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print 'm4b.py [-i <inputfile>] [-c <cover>] [-a <author>] [-t <title>]'
        sys.exit()
    elif opt == '-d':
        DEBUG=1
    elif opt in ("-i", "--ifile"):
        mp3_files = arg.split(',')
        debug ("file list is " + ",".join(mp3_files));

sys.exit();


# output dir
if not os.path.isfile("output"):
    os.mkdir("output")

# get mp3
mp3_files = [filename for filename in os.listdir(".") if filename.endswith(".mp3")]
mp3_files.sort()

print  mp3_files
# wrap mp3
subprocess.call(["mp3wrap"] + ["-v"] + ["output/output.mp3"] + mp3_files)

# convert to aac
ffmpeg = 'ffmpeg -i output/output_MP3WRAP.mp3 -y -vn -acodec libfaac -ab 128k -ar 44100 -f mp4 -threads 4 output/output.aac'
subprocess.call(ffmpeg.split(" "))

# create chapters file
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

chapters_file = open('output/chapters', 'w')

counter = 0
time = 0

artist, album_title = None, None

for filename in mp3_files:
    audio = MP3(filename, ID3=EasyID3)
    length = mad.MadFile(filename).total_time() / 1000. # don't use mutagen here, because it isn't very precise

    try:
        title = audio["title"][0]
    except:
        title = filename

    try:
        artist = audio["artist"][0]
    except:
        artist = "None"

    try:
        album_title = audio["album"][0]
    except:
        album_title = "None"


    counter += 1

    chapters_file.write("CHAPTER%i=%s\n" % (counter, secs_to_hms(time)))
    chapters_file.write("CHAPTER%iNAME=%s\n" % (counter, title.encode('utf-8')))

    time += length

chapters_file.close()

os.chdir("output")

# add chapters


subprocess.call(["MP4Box", "-add", "output.aac", "-chap", "chapters", "output.mp4"])

# convert chapters to quicktime format
subprocess.call(["mp4chaps", "--convert", "--chapter-qt", "output.mp4"])

# clean up
os.remove("chapters")
os.remove("output.aac")
os.remove("output_MP3WRAP.mp3")

# create tags, rename file
audio = MP4("output.mp4")
audio["\xa9nam"] = [album_title]
audio["\xa9ART"] = [artist]
audio.save()

if os.path.isfile("../cover.jpg"):
    subprocess.call(["mp4art", "--add", "../cover.jpg", "output.mp4"])


os.rename("output.mp4", "%s - %s.m4b" % (artist, album_title))

print
print "Now use iTunes or gtkPod>=v0.99.14 to transfer the audio book to your iPod."
print
