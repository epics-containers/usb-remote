# Connecting to GovWiFi

## Introduction

GovWiFi is a good choice for getting internet access on your usb-remote server if it is available to you. No complicated setup is required.

However you do need to use the Raspberry Pi OS with desktop (GUI) as the network manager used in the GUI version has support for the WPA-EAP protocol used by GovWiFi.

## Steps to connect to GovWiFi

1. Create an account using step 1. on the page [Gov Wifi](https://www.wifi.service.gov.uk/connect-to-govwifi/)
  - text 'Go' to 07537 417 417
  - send a blank email from your public sector email address to signup@wifi.service.gov.uk
  - you will receive an email with your username and password
1. On your Raspberry Pi desktop, click the network icon in the top right of the screen to get the network menu.
1. Select 'GovWifi' from the list of available networks.
1. You should be prompted with a configuration dialog.
  - The settings from this Android page should match what you see on your Raspberry Pi: [Gov Wifi Android Setup](https://www.wifi.service.gov.uk/device-android/)
    - Set EAP method to 'PEAP'
    - Set Phase 2 authentication to 'MSCHAPV2'
    - Set certificate to None
    - Set Domain to `wifi.service.gov.uk`
    - Set Anonymous identity to blank
    - Set Identity to your GovWiFi username (from the text you received)
    - Set Password to your GovWiFi password (from the text you received)
