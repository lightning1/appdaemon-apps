# appdaemon-apps
Useful applications for the homeassistant (HA) appdaemon.

## Apps
### Telegram AutoOff Notifications
If you regulary forget to turn off lights or other devices when you leave your home, this is what you want.
you have to use the HA telegram integrations.

With this app you can define sets of HA components related to users.
Users need a telegram notification component and at least one device tracker element.
When the last device of a set leaves (e.g. all devices of all users of a set) and some of the components are still turned on,
the owner of the tracked device gets a telegram notification that lists all components that are still online.
A keyboard with the option to turn off all entities is added to the notification.

## Setup
The following files need adjustments:
- appdaemon.example.yaml rename to appdaemon.yaml, the ha_url needs to point to your HA installation 
- secrets.yaml has to provide the API key for your HA installation
- apps/apps.example.yaml rename to apps/apps.yaml, adjust the instances to your needs
- apps/globals.yaml needs the HA elements to contact the users
