DEBUG_TO_WEB=False # True when debbugging

import logging
#--- select one of these options ---
#LOG_LEVEL=logging.ERROR
#LOG_LEVEL=logging.WARNING
#LOG_LEVEL=logging.INFO
LOG_LEVEL=logging.DEBUG

BASE_PATH='/path/to/this-folder'
BASE_URL='http://example.org/path/to/this-folder'

# Credits and ID3 info
ARTIST='DJ Vadim (remixed by SynPhonia user)'
ALBUM='Watch This Sound mixes'
EMPTY_MIX_HTML="""Empty or invalid mix. Try an <a href="?c0=_yjjrrsszz&c1=__llllkk_y&c2=__gggghh__&c3=addcbbacdd&s=-1">example</a>"""
CREDITS="""Samples are (<a target="_blank" href="http://creativecommons.org/licenses/by-nc/3.0/us/">cc</a>)
<a target="_blank" href="http://ccmixter.org/bbe">DJ Vadim</a>."""

#--- select one the option that works for your machine ---
SOX_MIX_COMMAND=['sox','-m'] # For most modern machines
#SOX_MIX_COMMAND=['soxmix'] # for old machines

LOG_FILE=BASE_PATH+'/.synphonia.log' # we don't want this available via web
WAV_SAMPLE_PATH=BASE_PATH+'/wav-samples'
WAV_MIX_PATH=BASE_PATH+'/wav-mixes'
SAMPLE_PATH=BASE_PATH+'/samples'
SAMPLE_URL=BASE_URL+'/samples'
MIX_PATH=BASE_PATH+'/mixes'
MIX_URL=BASE_URL+'/mixes'
FLASH_PLAYER_URL=BASE_URL+'/musicplayer.swf'

# These numbers affect cache disk consumption
WAV_CACHE_TRACKS=30
MP3_CACHE_TRACKS=100
MAX_BARS=32 # also limits sox cpu usage
