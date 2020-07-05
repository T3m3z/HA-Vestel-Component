# HA-Vestel-Component

This Home Assistant custom component allows one to interface some of TV sets manufactured by Vestel. It has been tested only using Procaster LE-50F449.

It uses [pyvesteltv](https://github.com/T3m3z/pyvesteltv) library.

## Installation

Copy folder `custom_components` to your config folder. Restart Home Assistant and hope for the best :)

## Limitations

TV cannot be turned on if it is turned off using remote control as this makes the TV disconnect from wifi. 

(Please note! These television sets are quite cheap. This implicates "interesting" APIs and therefore some interactions with the TV might seem a bit "hackish" :) For example TV seems to respond to some TCP commands with XML response and to some with `<key>:<value>`.)

## Configuration

Unfortunately I haven't implemented configuration through UI yet. Configura sources list to include sources of your television in the same order as they appear when you access sources list using remote control.

Parameter `supports_power` can be used to disable turn_on and turn_off services if you are using some other way to control turning on and off your TV (for example IR combined with Home Assistant).

```yaml
media_player:
  - platform: vestel
    host: 192.168.1.100
    name: Procaster
    supports_power: true # Can be used to disable 
    sources:
      - TV
      - Playstation 2
      - Playstation 3
      - Kodi
      - HDMI3/PC
      - VGA/PC
      - Netflix
      - YouTube
```

## Disclaimer

Unfortunately I don't have resources to create integrations for every possible Vestel TV set but I hope that this custom component together with [pyvesteltv](https://github.com/T3m3z/pyvesteltv) library will act as a starting point for you to create your own.