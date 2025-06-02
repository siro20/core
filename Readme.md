# Daikin P1/P2 integration

Home Assistant component for interacting with Daikin Altherma HeatPumps.

It has been tested with Daikin Hybrid Heatpump EJHA*, but should be compatible to most EHYB*.
You **need a custom P1/P2 serial gateway** to sniff the P1/P2 bus for example this one:
https://github.com/siro20/P1P2_HBS_USBCdc_Modem


This component uses information found by Arnold.
See https://github.com/Arnold-n/P1P2MQTT/blob/main/doc/LogicalFormat/Daikin-protocol-EHYHBX08AAV3.md

# Installation

## Manual

For this, it is highly recommended to use the "Samba share" add-on (you will need to enable advanced mode in your user profile).

Clone or download the repo, and copy the "homeassistant/components/daikin_p1p2bus/" folder to the "custom_components" folder in home assistant.

Restart homeassistant to reload the components.

After that, the folder structure should look as follows:

```bash
custom_components
├── daikin_p1p2bus
│   ├── binary_sensor.py
│   ├── config_flow.py
│   ├── const.py
│   ├── coordinator.py
│   ├── entity.py
│   ├── icons.json
│   ├── __init__.py
│   ├── manifest.json
│   ├── p1p2_base.py
│   ├── p1p2_parameter.py
│   ├── p1p2.py
│   ├── sensor.py
├── {other components}
```

## Setup

When installing the component specify the serial of the P1/P2 gateway.
Usually that's on of:
* `/dev/ttyUSB0`
* `/dev/ttyAMA0`
...

# Gateway

The Daikin P1/P2 gateway is supposed to sniff the P1/P2 bus and transmit the packets over the serial.
Every packet should be send as separate line containing an ASCII hex dump.

For example:

```
 0000100001010000000015004000000800001800403000f7
 400010000081013000180015005a000000000000400000d0
 0000111466000000000000b7
 4000111f3033a60f80274825981b2814660f81000000002c
```

