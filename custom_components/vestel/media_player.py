"""
Support for interfacing with the Procaster / Vestel televisions.
"""
import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK, SUPPORT_PLAY_MEDIA,
    SUPPORT_VOLUME_MUTE, SUPPORT_STOP, SUPPORT_TURN_ON, SUPPORT_PLAY, 
    SUPPORT_VOLUME_STEP, SUPPORT_VOLUME_SET, SUPPORT_TURN_OFF, SUPPORT_SELECT_SOURCE, 
    MEDIA_TYPE_CHANNEL)
from homeassistant.const import (
    STATE_IDLE, STATE_UNKNOWN, STATE_OFF, STATE_PAUSED, STATE_PLAYING, CONF_HOST, CONF_NAME,
    CONF_TIMEOUT, EVENT_HOMEASSISTANT_STOP)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "vestel"
DEFAULT_NAME = 'Vestel'
CONF_TCP_PORT = 'tcp_port'
CONF_WS_PORT = 'ws_port'
CONF_SOURCES = 'sources'
CONF_SUPPORT_POWER = 'supports_power'

DEFAULT_SOURCES = ["TV", "Netflix", "YouTube"]

SUPPORT_PROCASTER = SUPPORT_PAUSE | SUPPORT_VOLUME_MUTE | \
     SUPPORT_STOP | SUPPORT_PLAY | SUPPORT_VOLUME_STEP | \
     SUPPORT_VOLUME_SET | SUPPORT_NEXT_TRACK | SUPPORT_PREVIOUS_TRACK | \
     SUPPORT_PLAY_MEDIA | SUPPORT_SELECT_SOURCE

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TCP_PORT, default=1986): cv.port,
    vol.Optional(CONF_WS_PORT, default=7681): cv.port,
    vol.Optional(CONF_TIMEOUT, default=5): cv.positive_int,
    vol.Optional(CONF_SOURCES, default=DEFAULT_SOURCES): cv.ensure_list,
    vol.Optional(CONF_SUPPORT_POWER, default=True): cv.boolean
})


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Vestel platform."""
    host = config.get(CONF_HOST)

    entity = VestelDevice(
        hass,
        name=config.get(CONF_NAME),
        host=host,
        sources_list=config.get(CONF_SOURCES),
        support_power=config.get(CONF_SUPPORT_POWER))
    
    async_add_entities([entity], update_before_add=True)

class VestelDevice(MediaPlayerEntity):
    """Representation of a Vestel Smart TV."""

    def __init__(self, hass, name, host, sources_list, support_power):
        from pyvesteltv import Broadcast
        from pyvesteltv import VestelTV
        """Initialize the Procaster device."""
        self.hass = hass
        self._name = name
        self._host = host
        self._sources_list = sources_list
        self._current_source = self._sources_list[0]
        self._state = STATE_UNKNOWN
        self._volume = 0
        self._muted = False 
        self._ws_connected = False
        self.device = VestelTV(hass.loop, host)

        self._support = SUPPORT_PROCASTER

        if support_power:
          self._support |= SUPPORT_TURN_ON | SUPPORT_TURN_OFF

        def on_hass_stop(event):
            """Close websocket connection when hass stops."""
            self.hass.async_add_job(self.device._ws_close())

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, on_hass_stop)

        _LOGGER.info("Configured Vestel Device: %s", self._name)

    @asyncio.coroutine
    def async_sendKey(self, key):
        yield from self.device.sendkey(key)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self.device.get_volume()

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self.device.get_muted()

    @asyncio.coroutine
    def async_update(self):
        yield from self.device.update()
        if self.device.get_state():
          self._state = STATE_PLAYING
        else:
          self._state = STATE_OFF

        media_title = self.media_title if self.media_title else ""
        source = self.device.source
        if "TV" in media_title:
          self._current_source = "TV"
        elif media_title in self.source_list:
          self._current_source = media_title
        elif source in self.source_list:
          self._current_source = source

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        support = self._support
        if not self.device.discovered():
            support &= ~SUPPORT_TURN_ON
        return support

    @asyncio.coroutine
    def async_turn_off(self):
        """Execute turn_off_action to turn off media player."""
        if self._state is not STATE_OFF:
            yield from self.device.turn_off()
            self._state = STATE_OFF
            self.hass.async_add_job(self.async_update_ha_state())

    @asyncio.coroutine
    def async_turn_on(self):
        """Execute turn_on_action to turn on media player."""
        if self._state is STATE_OFF:
            yield from self.device.turn_on()
            self._state = STATE_PLAYING
            self.hass.async_add_job(self.async_update_ha_state())

    @asyncio.coroutine
    def async_volume_up(self):
        """Volume up the media player."""
        yield from self.device.volume_up()

    @asyncio.coroutine
    def async_volume_down(self):
        """Volume down the media player."""
        yield from self.device.volume_down()

    @asyncio.coroutine
    def async_set_volume_level(self, volume):
        """Set the volume of the media player."""
        yield from self.device.set_volume(volume)

    @asyncio.coroutine
    def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        yield from self.device.toggle_mute()

    @asyncio.coroutine
    def async_media_play(self):
        """Play media."""
        yield from self.device.sendkey(1025)
        self._state = STATE_PLAYING
        self.hass.async_add_job(self.async_update_ha_state())

    @asyncio.coroutine
    def async_media_pause(self):
        """Pause the media player."""
        yield from self.device.sendkey(1049)
        self._state = STATE_PAUSED  
        self.hass.async_add_job(self.async_update_ha_state())

    @asyncio.coroutine
    def async_media_stop(self):
        """Stop the media player."""
        yield from self.device.sendkey(1024)
        self._state = STATE_STOP
        self.hass.async_add_job(self.async_update_ha_state())

    @asyncio.coroutine
    def async_media_next_track(self):
        """Send next track command."""
        yield from self.device.next_track()

    @asyncio.coroutine
    def async_media_previous_track(self):
        """Send next previous command."""
        yield from self.device.previous_track()

    @asyncio.coroutine
    def async_play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        if media_type == MEDIA_TYPE_CHANNEL:
            channel = int(media_id)
            if channel > 99:
              yield from self.device.sendkey(1000 + int(channel/100))
            if channel > 9:
              yield from self.device.sendkey(1000 + int(channel/10))
            yield from self.device.sendkey(1000 - int(channel/10)*10 + channel)
            yield from self.device.sendkey(1053)

    @asyncio.coroutine
    def async_select_source(self, source):
        """Select input source."""
        if self.source == "Netflix":
            yield from self.device.stop_netflix()
            yield from asyncio.sleep(3)
        elif self.source == "YouTube":
            yield from self.device.stop_youtube()
            yield from asyncio.sleep(3)
    
        if source == "YouTube":
            yield from self.device.start_youtube()
        elif source == "Netflix":
            yield from self.device.start_netflix()
        else:
            yield from self.device.sendkey(1056)
            yield from self.device.sendkey(1001 + self.source_list.index(source))
        self._current_source = source

    @property
    def source(self):
        """Return the current input source."""
        return self._current_source

    @property
    def source_list(self):
        """List of available input sources."""
        return self._sources_list

    @property
    def media_title(self):
        """Title of current playing media."""
        return self.device.get_media_title()

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sun."""
        return {
            "last_ws": self.device.ws_state,
            "state": self.device.get_state(),
            "discovered": self.device.discovered(),
            "media_title": self.device.get_media_title()
        }
