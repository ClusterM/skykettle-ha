# Redmond SkyKettle integration for Home Assistant
This integration allows to control smart kettles from **Redmond SkyKettle** series.

![image](https://user-images.githubusercontent.com/4236181/151023077-ca0055b4-1b1d-41a6-879c-6aabe3a30164.png)

![image](https://user-images.githubusercontent.com/4236181/151022885-1a93c4d5-b5fe-40f2-8d1f-ddb458ea2c09.png)

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

## Donations

* PayPal: [clusterrr@clusterrr.com](https://www.paypal.me/clusterm)
* YooMoney: [41001843680639](https://yoomoney.ru/transfer/quickpay?requestId=343838343938323238305f64633138343335353537313930333165656235636336346136363334373439303432636264356532)
* Bitcoin: [1GS4XXx1FjQaFjgHnoPPVAzw9xqfv5Spx5](https://btc.clusterrr.com/)
* DonationAlerts: [https://www.donationalerts.com/r/clustermeerkat](https://www.donationalerts.com/r/clustermeerkat)
