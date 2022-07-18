# Redmond SkyKettle integration for Home Assistant
This integration allows to control smart kettles from **Redmond SkyKettle** series.

![image](https://user-images.githubusercontent.com/4236181/153447814-b2b3846d-e925-477f-ad7b-1f5639f7609a.png)

![image](https://user-images.githubusercontent.com/4236181/151023077-ca0055b4-1b1d-41a6-879c-6aabe3a30164.png)

![image](https://user-images.githubusercontent.com/4236181/151022885-1a93c4d5-b5fe-40f2-8d1f-ddb458ea2c09.png)

## Supported models
* **RK-M1**xx
* **RK-G2**xx
* **RK-M2**xx

## Features
* Allows to set target temperature.
* Allows to set any boil mode: heating (keep desired temperature), standard boiling, boiling+heating.
* Allows to change many settings of the kettle directly from Home Assistant, even more settings than the official application allows.
* Allows to read all statistics, even more than the official application allows.
* Allows to use kettle as RGB lamp.
* Automatic mode change if target temperature changed, allows easy control from Google Assistant, Yandex Alice, etc.
* Persistent connection and fast reconnect.

## Requirements

* Linux-based server with Home Assistant.
* Bluetooth adapter with BLE support.
* [timeout](https://command-not-found.com/timeout) utility.
* [hcitool](https://command-not-found.com/hcitool) utility.
* [gatttool](https://command-not-found.com/gatttool) utility.

## How to use

* Install it via [HACS](https://hacs.xyz/) - search for **SkyKettle** or just copy [skykettle](https://github.com/ClusterM/skykettle_ha/tree/master/custom_components/skykettle) directory to your `custom_components` directory.
* If you are not using **Home Assistant Operating System** make sure that `hcitool` and `getttool` (or just Home Assistant binary) has access to BLE device. To do it just execute those commands:
```
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which hcitool`
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which gatttool`
```
* Add **SkyKettle** integration just like any other integration (press Shift+F5 if it's not listed).
* Make sure that the Kettle is on the stand and it's plugged into the outlet.
* Select MAC address of your kettle from the list.
* Tune rest of the settings if you want.
* Enjoy.

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

* PayPal: [clusterrr@clusterrr.com](https://www.paypal.me/clusterm)
* YooMoney: [41001843680639](https://yoomoney.ru/transfer/quickpay?requestId=343838343938323238305f64633138343335353537313930333165656235636336346136363334373439303432636264356532)
* Bitcoin: [1GS4XXx1FjQaFjgHnoPPVAzw9xqfv5Spx5](https://btc.clusterrr.com/)
* DonationAlerts: [https://www.donationalerts.com/r/clustermeerkat](https://www.donationalerts.com/r/clustermeerkat)
