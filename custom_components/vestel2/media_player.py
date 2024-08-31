"""
Support for interfacing with the Procaster / Vestel televisions.
"""
#import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerEntityFeature, MediaPlayerEntity, PLATFORM_SCHEMA)
from homeassistant.const import (
    STATE_IDLE, STATE_UNKNOWN, STATE_OFF, STATE_PAUSED, STATE_PLAYING, CONF_HOST, CONF_NAME,
    CONF_TIMEOUT, EVENT_HOMEASSISTANT_STOP)
from homeassistant.helpers import config_validation as cv, entity_platform, service


from .vestel import *

_LOGGER = logging.getLogger(__name__)

DOMAIN = "vestel"
DEFAULT_NAME = 'Vestel'
CONF_TCP_PORT = 'tcp_port'
CONF_SOURCES = 'sources'
CONF_MAX_VOLUME = 'max_volume'
CONF_USE_HEADPHONEVOLUME = 'use_headphone_volume'

SERVICE_SEND_KEY = 'send_key'
SERVICE_SEND_COMMAND = 'send_command'

DEFAULT_SOURCES = ["TV", "HDMI1"]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TCP_PORT, default=1986): cv.port,
    vol.Optional(CONF_USE_HEADPHONEVOLUME, default=False): cv.boolean,
    vol.Optional(CONF_MAX_VOLUME, default=40): cv.positive_int,
    vol.Optional(CONF_SOURCES, default=DEFAULT_SOURCES): cv.ensure_list
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Setup the Vestel platform."""
    host = config.get(CONF_HOST)

    entity = VestelDevice(
        hass,
        name=config.get(CONF_NAME),
        host=host,
        sources_list=config.get(CONF_SOURCES),
        use_headphone_volume=config.get(CONF_USE_HEADPHONEVOLUME),
        max_volume=config.get(CONF_MAX_VOLUME))

    platform = entity_platform.current_platform.get()

    # Register service for sending key presses
    platform.async_register_entity_service(
        SERVICE_SEND_KEY,
        {
            vol.Required('key'): cv.string,
        },
        "async_send_key",
    )
    platform.async_register_entity_service(
        SERVICE_SEND_COMMAND,
        {
            vol.Required('command'): cv.string,
        },
        "async_send_command",
    )

    async_add_entities([entity], update_before_add=True)
    return True

class VestelDevice(MediaPlayerEntity):
    """Representation of a Vestel Smart TV."""

    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.TURN_OFF
    )

    

    def __init__(self, hass, name, host, sources_list, use_headphone_volume, max_volume):
        #from pyvesteltv import Broadcast
        #from vestel import *
        """Initialize the Procaster device."""
        self.hass = hass
        self._name = name
        self._host = host
        self._sources_list = sources_list
        self._current_source = self._sources_list[0]
        self._state = STATE_UNKNOWN
        self._volume = 0
        self._muted = False
        self._max_volume = max_volume
        self.device = VestelHelper(host)
        self._volume_command = "HEADPHONEVOLUME" if use_headphone_volume else "VOLUME"

        def on_hass_stop(event):
            """Close websocket connection when hass stops."""
            self.hass.async_create_task(self.device.writer.close())

        self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, on_hass_stop)

        _LOGGER.info("Configured Vestel Device: %s", self._name)

    async def async_send_key(self, key):
        await self.device.sendkey(key)

    async def async_send_command(self, command):
        await self.device.command(command, expect_response=True)

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._volume_command in self.device.attributes:
          return min(int(self.device.attributes[self._volume_command])/self._max_volume,1)
        return 0

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        if "MUTE" in self.device.attributes:
          return self.device.attributes["MUTE"] == "ON"
        return False

    async def async_update(self):
        await self.device.update()
        if self.device.state:
          self._state = STATE_PLAYING
        else:
          self._state = STATE_OFF

        if "SOURCE" in self.device.attributes:
          source = self.device.attributes["SOURCE"]
          if source not in self._sources_list:
            self._sources_list.append(source)
          self._current_source = source

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return True

    async def async_turn_off(self):
        """Execute turn_off_action to turn off media player."""
        if self._state is not STATE_OFF:
            await self.device.command("STANDBY", expect_response=False)
            self._state = STATE_OFF
            self.async_write_ha_state()

    async def async_turn_on(self):
        """Execute turn_on_action to turn on media player."""
        if self._state is STATE_OFF:
            await self.device.command("STANDBY", expect_response=False)
            self._state = STATE_PLAYING
            self.async_write_ha_state()

    async def async_volume_up(self):
        """Volume up the media player."""
        await self.device.sendkey("vol+")

    async def async_volume_down(self):
        """Volume down the media player."""
        await self.device.sendkey("vol-")

    async def async_set_volume_level(self, volume):
        """Set the volume of the media player."""
        await self.device.command("{} {}".format(self._volume_command, int(volume*self._max_volume)))

    async def async_mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        await self.device.command("SETMUTE")

    async def async_media_play(self):
        """Play media."""
        await self.device.sendkey("play")
        self._state = STATE_PLAYING
        self.hass.async_add_job(self.async_update_ha_state())

    async def async_media_pause(self):
        """Pause the media player."""
        await self.device.sendkey("pause")
        self._state = STATE_PAUSED
        self.hass.async_add_job(self.async_update_ha_state())

    async def async_media_stop(self):
        """Stop the media player."""
        await self.device.sendkey("stop")
        self._state = STATE_STOP
        self.hass.async_add_job(self.async_update_ha_state())

    async def async_media_next_track(self):
        """Send next track command."""
        if self._current_source.startswith("TV"):
            await self.device.sendkey("prog+")
        else:
            await self.device.sendkey("fforward")

    async def async_media_previous_track(self):
        """Send next previous command."""
        if self._current_source.startswith("TV"):
            await self.device.sendkey("prog-")
        else:
            await self.device.sendkey("rewind")

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        if media_type == MEDIA_TYPE_CHANNEL:
            channel = int(media_id)
            if channel > 99:
              await self.device.sendkey(int(channel/100))
            if channel > 9:
              await self.device.sendkey(int(channel/10))
            await self.device.sendkey(int(channel/10)*10 + channel)
            await self.device.sendkey("ok")

    async def async_select_source(self, source):
        """Select input source."""
        await self.device.sendkey("aux")
        await self.device.sendkey(1 + self.source_list.index(source))
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
        """List of available input sources."""
        if self._current_source == "TV" and "PROGRAM" in self.device.attributes:
          return self.device.attributes["PROGRAM"]
        return self._current_source
