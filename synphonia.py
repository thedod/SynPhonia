#!/usr/local/bin/python2.6
""" For more info: http://wiki.github.com/thedod/SynPhonia/ """
#   SynPhonia - a cellular-friendly web-based music sequencer toy
#   Copyright (C) 2010 Nimrod S. Kerrett (@TheRealDod)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


#################################begin config#################################

#synconf.py should look like:
#BASE_PATH='/path/to/this-folder'
#BASE_URL='http://example.org/path/to/this-folder'
##Uncomment one of the following:
#SOX_MIX_COMMAND=['sox','-m'] # For most modern machines
##SOX_MIX_COMMAND=['soxmix'] # for old machines

from synconf import BASE_PATH,BASE_URL,SOX_MIX_COMMAND

WAV_CACHE_TRACKS=30
MP3_CACHE_TRACKS=100
MAX_BARS=16 # against DoS
ARTIST='DJ Vadim (remixed by SynPhonia user)'
ALBUM='Watch This Sound mixes'
EMPTY_MIX_HTML="""Empty or invalid mix. Try an <a href="?c0=_yjjrrsszz&c1=__hhgglk&c2=addcbbacdd">example</a>"""
DEBUG_TO_WEB=True # Should be False ;)
import logging
#--- uncomment one of the options ---
#LOG_LEVEL=logging.ERROR
#LOG_LEVEL=logging.WARNING
#LOG_LEVEL=logging.INFO
LOG_LEVEL=logging.DEBUG

#############################begin low level config############################
LOG_FILE=BASE_PATH+'/.synphonia.log' # we don't want this available via web
WAV_SAMPLE_PATH=BASE_PATH+'/wav-samples'
WAV_MIX_PATH=BASE_PATH+'/wav-mixes'
SAMPLE_PATH=BASE_PATH+'/samples'
SAMPLE_URL=BASE_URL+'/samples'
MIX_PATH=BASE_PATH+'/mixes'
MIX_URL=BASE_URL+'/mixes'
FLASH_PLAYER_URL=BASE_URL+'/musicplayer.swf'

PAGE_TEMPLATE="""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"> 
 <head> 
  <title>SynPhonia</title> 
  <link rel="stylesheet" href="stylee.css" type="text/css" />
  <script language="javascript"> 
   playerbutton=function(path,track) {{
    document.write(
     '<object type="application/x-shockwave-flash" data="{flash_player_url}?playlist_url='+
     path+'/'+track+'.xspf&b_bgcolor=&b_fgcolor=cf3f3f" width="17" height="17"><param name="wmode" value="transparent"></object>' 
    );
   }}
  </script> 
 </head> 
 <body> 
  {form}
  {errors}
  {mix}
  <hr/>
  Samples: {samples}<br/>
  <small>1 letter = 1 bar, _ = silence, Case insensitive<br/>
  Samples are (<a target="_blank" href="http://creativecommons.org/licenses/by-nc/3.0/us/">cc</a>)
  <a target="_blank" href="http://ccmixter.org/bbe">DJ Vadim</a></small>
 </body>
</html>
"""
FORM_TEMPLATE="""<form method="GET" action="{action}"> 
   <input name="c0" value="{0}"><br/> 
   <input name="c1" value="{1}"><br/> 
   <input name="c2" value="{2}">
   <input type="submit" value="Remix">
  </form> 
"""

TRACK_TEMPLATE="""<script language="javascript">playerbutton('{path}','{track}')</script>""" + \
"""<a href="{path}/{track}.mp3">{track}</a>
"""

XSPF_TEMPLATE="""<?xml version="1.0" encoding="utf-8"?>
<playlist version="1" xmlns="http://xspf.org/ns/0/">
  <title>{track}</title>
  <annotation>{track}</annotation>
  <creator>{artist}</creator>
  <license>http://creativecommons.org/licenses/by-nc-sa/3.0/</license>
  <trackList>
    <track>
      <location>{url_path}/{track}.mp3</location>
      <title>{track}</title>
      <creator>{artist}</creator>
      <album>{album}</album>
    </track>
  </trackList>
</playlist>"""
#################################end config#################################

logging.basicConfig(level=LOG_LEVEL, datefmt='%Y-%m-%d %H:%M:%S',
                    format='%(asctime)s %(levelname)s: %(message)s',
                    filename=LOG_FILE, filemode='a')

import os,shutil,re,subprocess,cgi
from exceptions import Exception
import eyeD3

def touch_if_exists(path):
    """If file exists, touch it and return True, else return False.
       Utime is used by cleanup_cache() to delete least recently used files"""
    if os.access(path,os.F_OK):
        logging.debug('cache hit: %s',path)
        os.utime(path,None)
        return True
    else:
        return False

def cleanup_cache(folder,keep=100):
    files=['{0}/{1}'.format(folder,f) for f in os.listdir(folder)]
    if len(files)<keep:
        return
    files=[(os.stat(f).st_mtime,f) for f in files]
    files.sort()
    files=[f[1] for f in files[:-keep]]
    logging.debug('removing from cache: %s',map(os.path.basename,files))
    for f in files:
        os.unlink(f)

def run_or_delete(args,delete_if_failed=None,cwd=None):
        logging.debug('running %s',' '.join(args))
        proc=subprocess.Popen(args, cwd=cwd,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err=proc.communicate()
        if err:
            if delete_if_failed:
                logging.error('%s(%s) Failed: %s',args[0],os.path.basename(delete_if_failed),err)
                try:
                    os.unlink(delete_if_failed)
                except:
                    pass
            else:
                logging.error('%s Failed: %s',args[0],err)
            return err
        return None

def _get_sample_names():
    res=[f.split('.')[0] for f in os.listdir(WAV_SAMPLE_PATH) if f.endswith('.wav')]
    res.sort()
    return res

SAMPLE_NAMES=_get_sample_names()
SAMPLE_PATTERN=re.compile('|'.join(SAMPLE_NAMES))

def make_xspf(track,xspf_path=MIX_PATH,url_path=MIX_URL):
    filepath='{0}/{1}.xspf'.format(xspf_path,track)
    if not touch_if_exists(filepath):
        file(filepath,'w').write(
            XSPF_TEMPLATE.format(track=track,url_path=url_path,
                                 artist=ARTIST,album=ALBUM))
    return filepath

def write_id3(filepath,title,artist=ARTIST,album=ALBUM):
    id3=eyeD3.Tag()
    id3.link(filepath)
    id3.header.setVersion(eyeD3.ID3_V2_3)
    id3.setTitle(title)
    id3.setArtist(artist)
    id3.setAlbum(album)
    id3.update()

def parse_channel(s):
    """Returns list of sample basenames (without the .wav) found in s
       Whatever isn't a sample name gets thrown away.
       We convert s to lowercase because phones tend to capitalize. 
       We truncate the result to MAX_BARS or DoS attack could create
       huge wavs, thus hogging disk and CPU"""
    return SAMPLE_PATTERN.findall(s.lower())[:MAX_BARS]

def make_channel(samples):
    basename=''.join(samples)
    filepath='{0}/{1}.wav'.format(WAV_MIX_PATH,basename)
    if not touch_if_exists(filepath): # Not in cache? generate.
        filenames=[s+'.wav' for s in samples]
        err=run_or_delete(['sox']+filenames+[filepath],filepath,WAV_SAMPLE_PATH)
        if err:
            return None,["Concatenation error ({0}): {1}".format(basename,err)]
    return filepath,basename

def make_mix(channel_strings):
    channel_lists=map(parse_channel,channel_strings)
    parsed_values=[''.join(l) for l in channel_lists]
    channel_names=filter(None,parsed_values)
    if not channel_names:
        return None,parsed_values,[EMPTY_MIX_HTML]
    basename='-'.join(channel_names)
    filepath='{0}/{1}.mp3'.format(MIX_PATH,basename)
    errors=[]
    if not touch_if_exists(filepath): # Not in cache? generate.
        wavname=basename+'.wav'
        wavpath='{0}/{1}'.format(WAV_MIX_PATH,wavname)
        channel_pairs=map(make_channel,filter(None,channel_lists))
        errors=[p[1] for p in channel_pairs if not p[0]]
        channels=[p[0] for p in channel_pairs if p[0]]
        if not channels:
            return None,parsed_values,[EMPTY_MIX_HTML]
        if len(channels)==1: # Single channel. No need to mix
            pass
        else: # Mix the wavs
            err=run_or_delete(SOX_MIX_COMMAND+channels+[wavname],wavpath,WAV_MIX_PATH)
            if err:
                return None,parsed_values,["Mix error ({0}): {1}".format(basename,err)]
        ### Convert to mp3
        err=run_or_delete(['lame','--silent',wavname,filepath],filepath,WAV_MIX_PATH)
        if err:
            return None,parsed_values,["Conversion error ({0}): {1}".format(basename,err)]
        os.unlink(wavpath) # Unlike channels, mix wavs aren't cached, because we have mp3
        ### Write id3 tag
        write_id3(filepath,basename)
    ### make (or touch) the xspf file
    make_xspf(basename)
    cleanup_cache(WAV_MIX_PATH,WAV_CACHE_TRACKS)
    cleanup_cache(MIX_PATH,2*MP3_CACHE_TRACKS) # each track has .mp3 and .xspf files
    return basename,parsed_values,errors

def do_cgi():
    try:
        script_name=os.environ['SCRIPT_NAME']
    except: 
        raise Exception,"Program should run as a cgi"
    os.environ['TERM']='vt100' # to fool old version of lame that needs this
    fields = cgi.FieldStorage()
    channels=[fields.getvalue('c{0}'.format(i),'') for i in range(3)]
    track,parsed_values,errors=make_mix(channels)
    form_html=FORM_TEMPLATE.format(*parsed_values,action=script_name)
    errors_html=errors and """<div class="errors">{0}</div>""".format('<br/>\n'.join(errors)) or ""
    mix_html=track and  """<div class="mix">mix: {0}</div>""".format(
                           TRACK_TEMPLATE.format(path=MIX_URL,track=track)) or ""
    samples_html=''.join([TRACK_TEMPLATE.format(path=SAMPLE_URL,track=s) for s in SAMPLE_NAMES])
    page_html=PAGE_TEMPLATE.format(flash_player_url=FLASH_PLAYER_URL,form=form_html,
                                   errors=errors_html,mix=mix_html,samples=samples_html)
    print """Content-type:text/html; charset=utf-8

{0}""".format(page_html)

def init_samples():
    """When you add new samples to WAV_SAMPLE_PATH, you should:
       1) Add their respective mp3 files to SAMPLE_PATH
       2) Run init_samples() to id3-tag thwem andcreate their
          xspf files for the flash player"""
    for s in SAMPLE_NAMES:
        write_id3('{0}/{1}.mp3'.format(SAMPLE_PATH,s),s)
        make_xspf(s,SAMPLE_PATH,SAMPLE_URL)

if __name__=='__main__':
    if DEBUG_TO_WEB:
        import cgitb; cgitb.enable()
    do_cgi()
