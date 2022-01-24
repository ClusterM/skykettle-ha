# Redmond SkyKettle integration for Home Assistant
This integration allows to control smart kettles from **Redmond SkyKettle** series.

![image](https://user-images.githubusercontent.com/4236181/150850436-d8019861-9b2e-46ed-a462-69d3c92b9e6b.png)

Features:
* Allows to set target temperature.
* Allows to set any boil mode: heating (keep desired temperature), standard boiling, boiling+heating.
* Allows to change many settings of the kettle directly from Home Assistant, even more settings than the official application allows.
* Allows to read all statistics, even more than the official application allows.
* Allows to use kettle as RGB lamp.
* Automatic mode change if target temperature changed, allows easy control from Google Assistant, Yandex Alice, etc.
* Persistent connection and fast reconnect.

## How to use

* Install it via [HACS](https://hacs.xyz/) - search for **SkyKettle** or just copy [skykettle](https://github.com/ClusterM/skykettle_ha/tree/master/custom_components/skykettle) directory to your `custom_components` directory.
* If you are not using **Home Assistant Operating System** make sure that `hcitool` and `getttool` (or just Home Assistant binary) has access to BLE device. To do it just execute those commands:
```
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which hcitool`
sudo setcap 'cap_net_raw,cap_net_admin+eip' `which gatttool`
```
* Add **SkyKettle** integration just like any other integration.
* Make sure that the Kettle is on the stand and it's plugged into the outlet.
* Select MAC address of your kettle from the list.
* Tune rest of the settings if you want.
* Enjoy.
