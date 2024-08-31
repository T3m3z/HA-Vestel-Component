# HA-Vestel-Component

This Home Assistant custom component allows one to interface some of TV sets manufactured by Vestel. It has been tested only using Procaster LE-50F449.

It uses [pyvesteltv](https://github.com/T3m3z/pyvesteltv) library.

## Installation

Copy folder vestel2 to your `custom_components` folder on Home Assistant server. Restart Home Assistant and hope for the best :)

## Limitations

TV cannot be turned on if it is turned off using remote control as this makes the TV disconnect from wifi. 

(Please note! These television sets are quite cheap. This implicates "interesting" APIs and therefore some interactions with the TV might seem a bit "hackish" :) For example TV seems to respond to some TCP commands with XML response and to some with `<key>:<value>`.)

## Configuration

Unfortunately I haven't implemented configuration through UI yet. Configure sources list to include sources of your television in the same order as they appear when you access sources list using remote control.

```yaml
media_player:
  - platform: vestel2
    host: !secret vestelhost
    name: "Procaster"
    use_headphone_volume: false
    sources:
      - TV
      - HDMI1
      - HDMI2
      - HDMI3
      - VGA/PC
```

## Disclaimer

Unfortunately I don't have resources to create integrations for every possible Vestel TV set but I hope that this custom component together with [pyvesteltv](https://github.com/T3m3z/pyvesteltv) library will act as a starting point for you to create your own.