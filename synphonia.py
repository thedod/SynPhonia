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


# You should copy synconf_example.py to synconf.py
# And then edit it according to the comments there
from synconf import *

PAGE_TEMPLATE="""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"> 
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en"> 
 <head> 
  <title>SynPhonia</title> 
  <link rel="stylesheet" href="stylee.css" type="text/css" />
  <script language="javascript"> 
   playerbutton=function(path,track,flash_args) {{
    document.write(
     '<object type="application/x-shockwave-flash" data="{flash_player_url}?playlist_url='+
     path+'/'+track+'.xspf&autoload=true&b_bgcolor=&b_fgcolor=cf3f3f'+flash_args+'" width="17" height="17"><param name="wmode" value="transparent"></object>' 
    );
   }}
  </script> 
 </head> 
 <body> 
  {form}
  {errors}
  {mix}{sharelink}
  <hr/>
  Samples: {samples}<br/>
  {credits}
  [<b><a target="_blank" href="index.html">Help</a></b>]
 </body>
</html>
"""
# The s="-1" kludge: we don't want s="" because some browsers
# don't select the radio button in that case, so any non-numeric s
# is considered "no solo", and we use -1 because it sorta makes sense :)
# "" would still work (e.g. if you skip s= in url) since it's non-numeric.
FORM_TEMPLATE="""<form method="GET" action="{action}"> 
       <input name="c0" value="{0}">
       <input type="radio" name="s" value="0"{solo0}/>Solo
       <br/>
       <input name="c1" value="{1}">
       <input type="radio" name="s" value="1"{solo1}/>
       <br/>
       <input name="c2" value="{2}">
       <input type="radio" name="s" value="2"{solo2}/>
       <br/>
       <input name="c3" value="{3}">
       <input type="radio" name="s" value="3"{solo3}/>
       <br/>
       <input type="submit" value="Remix"/>
       <small><input type="checkbox" name="autoplay"{autoplay_checked}/>Auto Play</small>
       <input type="radio" name="s" value="-1"{nosolo}/>No solo
</form> 
"""

TRACK_TEMPLATE="""<script language="javascript">playerbutton('{path}','{track}','{flash_args}')</script>""" + \
"""<a href="{path}/{track}.mp3">{title}</a>
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

def make_mix(channel_strings,solo):
    channel_lists=map(parse_channel,channel_strings)
    parsed_values=[''.join(l) for l in channel_lists]
    # the prefix actual_ means only solo track (or all if no solo)
    if solo.isdigit():
        isolo=int(solo)%4 # avoid IndexError if e.g. s=42 in url :)
        actual_channel_lists=[channel_lists[isolo]]
        actual_parsed_values=[parsed_values[isolo]]
    else:
        actual_channel_lists=channel_lists
        actual_parsed_values=parsed_values
    actual_channel_names=filter(None,actual_parsed_values)
    if not actual_channel_names:
        return None,parsed_values,[EMPTY_MIX_HTML]
    basename='-'.join(actual_channel_names)
    filepath='{0}/{1}.mp3'.format(MIX_PATH,basename)
    errors=[]
    if not touch_if_exists(filepath): # Not in cache? generate.
        wavname=basename+'.wav'
        wavpath='{0}/{1}'.format(WAV_MIX_PATH,wavname)
        channel_pairs=map(make_channel,filter(None,actual_channel_lists))
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
    if DEBUG_TO_WEB:
        import cgitb; cgitb.enable()

    # If ugcurl was configured, we'll show share/submit link
    # See README
    use_sharelink=False
    try:
        from ugcurl import whatconf
        use_sharelink=True
    except:
        pass
    os.environ['TERM']='vt100' # to fool old version of lame that needs this
    fields = cgi.FieldStorage()
    channels=[fields.getvalue('c{0}'.format(i),'') for i in range(4)]
    autoplay=fields.getvalue('autoplay','')
    solo=fields.getvalue('s','')
    track,parsed_values,errors=make_mix(channels,solo)
    form_html=FORM_TEMPLATE.format(*parsed_values,action=script_name,
        solo0 = solo=='0' and ' checked="checked"' or '',
        solo1 = solo=='1' and ' checked="checked"' or '',
        solo2 = solo=='2' and ' checked="checked"' or '',
        solo3 = solo=='3' and ' checked="checked"' or '',
        nosolo = not solo.isdigit() and ' checked="checked"' or '', # see s="-1" kludge above
        autoplay_checked=autoplay and ' checked="checked"' or '')
    errors_html=errors and """<div class="errors">{0}</div>""".format('<br/>\n'.join(errors)) or ""
    mix_html=track and  """<span class="mix">mix: {0}</span>""".format(
                           TRACK_TEMPLATE.format(path=MIX_URL,track=track,title='MP3',
                                                 flash_args=autoplay and "&autoplay=true" or "")) or ""
    sharelink=use_sharelink and track and """ [<a target="_blank" href="ugcurl/">Share/Submit</a>]""" or ""
    samples_html=''.join([TRACK_TEMPLATE.format(path=SAMPLE_URL,track=s,title=s,flash_args="") for s in SAMPLE_NAMES])
    page_html=PAGE_TEMPLATE.format(flash_player_url=FLASH_PLAYER_URL,form=form_html,credits=CREDITS,
                                   errors=errors_html,mix=mix_html,samples=samples_html,sharelink=sharelink)
    print """Content-type:text/html; charset=utf-8

{0}""".format(page_html)

def init_samples():
    """When you add new samples to WAV_SAMPLE_PATH, you should:
       1) Add their respective mp3 files to SAMPLE_PATH
       2) Run init_samples() to id3-tag them and create their
          xspf files for the flash player
See README file for details"""
    for s in SAMPLE_NAMES:
        write_id3('{0}/{1}.mp3'.format(SAMPLE_PATH,s),s)
        make_xspf(s,SAMPLE_PATH,SAMPLE_URL)

if __name__=='__main__':
    do_cgi()
