# Redmond SkyKettle integration for Home Assistant
This integration allows to control smart kettles from **Redmond SkyKettle** series.

![image](https://user-images.githubusercontent.com/4236181/153447814-b2b3846d-e925-477f-ad7b-1f5639f7609a.png)

![image](https://user-images.githubusercontent.com/4236181/151023077-ca0055b4-1b1d-41a6-879c-6aabe3a30164.png)

![image](https://user-images.githubusercontent.com/4236181/151022885-1a93c4d5-b5fe-40f2-8d1f-ddb458ea2c09.png)

## Supported models
* RK-G200
* RK-G200S
* RK-G201S
* RK-G202S
* RK-G203S
* RK-G204S
* RK-G210S
* RK-G211S
* RK-G212S
* RK-G213S
* RK-G214S
* RK-G215S
* RK-G233S
* RK-G240S
* RK-M139S
* RK-M171S
* RK-M215S
* RK-M216S
* RK-M223S
* RK-M136S
* RFS-KKL002
* RFS-KKL003
* RFS-KKL004
* ???

If your kettle model is not listed, please write an [issue](https://github.com/ClusterM/skykettle-ha/issues) and I'll try to add support for it with your help. Models RK-M123S, RK-M170S and RK-M173S are especially wanted.

## Features
* Allows to set target temperature.
* Allows to set any boil mode: heating (keep desired temperature), standard boiling, boiling+heating.
* Allows to change many settings of the kettle directly from Home Assistant, even more settings than the official application allows.
* Allows to read all statistics, even more than the official application allows.
* Allows to use kettle as RGB lamp.
* Automatic mode change if target temperature changed, allows easy control from Google Assistant, Yandex Alice, etc.
* Persistent connection and fast reconnect.

## Requirements
* Bluetooth adapter with BLE support.
* Home Assistant [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) (comes with Home Assistant v2022.8.1+)

## How to use
* Make sure that you are using Home Assistant version 2022.8.1 or greater.
* Make sure that [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) is installed, enabled and working.
* Install **SkyKettle** integration via [HACS](https://hacs.xyz/) - search for **SkyKettle** or just copy [skykettle](https://github.com/ClusterM/skykettle_ha/tree/master/custom_components/skykettle) directory to your `custom_components` directory.
* Add **SkyKettle** integration just like any other integration (restart Home Assistant and press Shift+F5 if it's not listed).
* Make sure that the Kettle is on the stand and it's plugged into the outlet.
* Select MAC address of your kettle from the list.
* Tune rest of the settings if you want.
* Enjoy.

## Entities
The default entity names are listed below. Note that some entities can be missed on your kettle model.

### water_heater.*kettle_model*
This is main entity to control water boiling and heating. There are five operation modes:
* Off - the kettle is off, not heating at all.
* Heat - just heat water to the desired temperature and keep this temperature. Without boiling. Useful when water already boiled and you need just to warm it up.
* Boil - boil water and turn off (switch to "Off" mode).
* Boil+heat - boil water, wait until temperature drops to the desired temperature and keep this temperature.
* Lamp - use kettle as night light, color changes between the selected ones (see below).
* Light - use kettle as night light but keep the only one selected color (see below).

### light.*kettle_model*_light (Light)
This entity allows to control the "Light" mode. You can select brightness and color when this mode is active. The "Light" mode will be enabled automatically when this virtual light is on.

### switch.*kettle_model*
Just virtual switch to control the kettle. Turn it on to switch the kettle to "Boil" mode and turn it off for "Off" mode.

### sensor.*kettle_model*_water_freshness
Virtual sensor to check how long the water has been in the kettle. Actually, it's just kettle uptime.

### number.*kettle_model*_boil_time (Boil time)
This is configuration entity to select boil time from -5 to +5 just like in the official app.

### switch.*kettle_model*_enable_boil_light (Enable boil light)
This is configuration entity to enable or disable the boil light. This light in on when "Heat", "Boil" or "Boil+Heat" mode is active. Color depends on the current water temperature (see below).

### switch.*kettle_model*_enable_sound (Enable sound).
This is configuration entity to enable or disable kettle beeping sounds.

### switch.*kettle_model*_enable_sync_light (Enable sync light)
This is configuration entity to enable or disable the idle light. This light in on when "Off" mode is active. Color depends on the current water temperature (see below).

### light.*kettle_model*_lamp_1_color (Lamp color #1), light.*kettle_model*_lamp_2_color (Lamp color #2) and light.*kettle_model*_lamp_3_color (Lamp color #3)
These are three configuration entities to select colors in the "Lamp" mode. The color will change smoothly from #1 to #2, from #2 to #3 and back.

### number.*kettle_model*_lamp_color_change_interval (Lamp color change interval)
This is configuration entity to select color change interval in the "Lamp" mode. In seconds. Minimum is 30 seconds.

### number.*kettle_model*_lamp_auto_off_time (Lamp auto off time)
This is configuration entity to select lamp auto off time in hours. Lamp will be turned off after this time passed.

### number.*kettle_model*_temperature_1 (Temperature #1), light.*kettle_model*_temperature_1_color (Temperature #1 color), number.*kettle_model*_temperature_2 (Temperature #2), light.*kettle_model*_temperature_2_color  (Temperature #2 color) and number.*kettle_model*_temperature_3 (Temperature #3), light.*kettle_model*_temperature_3_color (Temperature #3 color)
These are six configuration entities to select colors for the "boil light" and "sync light". You can select three colors and temperature for each color. The color will change smoothly.

### sensor.skykettle_rk_g211s_success_rate (Success rate)
Diagnostic entity, shows percent of successfull connections and polls.

## Scripts
### To boil and turn off after boiling
```YAML
sequence:
  - service: water_heater.set_operation_mode
    data:
      operation_mode: Boil
    target:
      entity_id: water_heater.skykettle_rk_g211
```

Also you can use `water_heater.turn_on` service **when the kettle is off/idle**:
```YAML
sequence:
  - service: water_heater.turn_on
    data: {}
    target:
      entity_id: water_heater.skykettle_rk_g211
```

### To boil and keep desired temperature
```YAML
sequence:
  - service: water_heater.set_operation_mode
    data:
      operation_mode: Boil+Heat
    target:
      entity_id: water_heater.skykettle_rk_g211
  - service: water_heater.set_temperature
    data:
      temperature: 90
    target:
      entity_id: water_heater.skykettle_rk_g211
```

### To warm up and keep desired temperature without boiling
```YAML
sequence:
  - service: water_heater.set_operation_mode
    data:
      operation_mode: Heat
    target:
      entity_id: water_heater.skykettle_rk_g211
  - service: water_heater.set_temperature
    data:
      temperature: 90
    target:
      entity_id: water_heater.skykettle_rk_g211
```

### Turn the kettle off
```YAML
sequence:
  - service: water_heater.set_operation_mode
    data:
      operation_mode: off
    target:
      entity_id: water_heater.skykettle_rk_g211
```
Also you can use `water_heater.turn_off` service:
```YAML
sequence:
  - service: water_heater.turn_off
    data: {}
    target:
      entity_id: water_heater.skykettle_rk_g211
```

### Turn the kettle into a lamp
```YAML
sequence:
  - service: light.turn_on
    data:
      rgb_color:
        - 255
        - 100
        - 255
      brightness: 255
    target:
      entity_id: light.skykettle_rk_g211_light
```

## Hints
You can use the [card_mod](https://github.com/thomasloven/lovelace-card-mod) integration to make the color of the card icon depend on the temperature of the kettle.

Example:

```
type: vertical-stack
cards:
  - type: button
    tap_action:
      action: more-info
    entity: water_heater.skykettle_rk_g211
    show_state: true
    name: Чайник
    hold_action:
      action: toggle
    card_mod:
      style: >
        {% set temp = state_attr("water_heater.skykettle_rk_g211",
        "current_temperature") %}

        :host {
          --card-mod-icon:
          {% if temp != None and temp > 95 %}
          mdi:kettle-steam;
          {% else %}
          mdi:kettle;
          {% endif %}
          --card-mod-icon-color:
          {% if temp != None -%}
          hsl(
            {{ 235 + (0 - 235) / (95 - 25) * (temp - 25) }},
            {{ 60 + (100 - 60) / (100 - 25) * (temp - 25) }}%,
            50%
          )
          {%- else -%}
          black
          {%- endif %};
        }
  - type: entities
    entities:
      - entity: water_heater.skykettle_rk_g211
        card_mod:
          style: >
            {% set temp = state_attr("water_heater.skykettle_rk_g211",
            "current_temperature") %}

            :host {
              --card-mod-icon:
              {% if temp != None and temp > 95 %}
              mdi:kettle-steam;
              {% else %}
              mdi:kettle;
              {% endif %}
              --card-mod-icon-color:
              {% if temp != None -%}
              hsl(
                {{ 235 + (0 - 235) / (95 - 25) * (temp - 25) }},
                {{ 60 + (100 - 60) / (100 - 25) * (temp - 25) }}%,
                50%
              )
              {%- else -%}
              black
              {%- endif %};
            }
```

![image](https://user-images.githubusercontent.com/4236181/153446401-45c2f09e-2637-4fd1-8dec-0c365a3babb5.png)

## Donations
* YooMoney: [41001843680639](https://yoomoney.ru/transfer/quickpay?requestId=343838343938323238305f64633138343335353537313930333165656235636336346136363334373439303432636264356532)
* Bitcoin: [1GS4XXx1FjQaFjgHnoPPVAzw9xqfv5Spx5](https://btc.clusterrr.com/)
* DonationAlerts: [https://www.donationalerts.com/r/clustermeerkat](https://www.donationalerts.com/r/clustermeerkat)
