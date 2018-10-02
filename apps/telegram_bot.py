import appdaemon.plugins.hass.hassapi as hass
import globals
import os

#
# App to request to turn off stuff left powered on
#
# Args:
# users: list of global config users (identifiers as strings) to use for the instance 
# entities: list of stuff that should be off
# instance_name: identifier of this PowerOff-App
#
# Version 1.0:
#   Initial Version

class TelegramAutoOff(hass.Hass):

  def initialize(self):

    if len(self.args["users"]) < 1:
        self.log("No users configured!")

    # list all tracked devices in log
    for user in self.args["users"]:
        if user in globals.users:
            user_data = globals.users[user]
            if "tracked_devices" in user_data:
                for tracked_device in user_data["tracked_devices"]:
                    self.log("Tracking device " + str(tracked_device) + " of user " + str(user))
        else:
            self.log("The user " + str(user) + " could not be found in the global configuration!")
    self.listen_state(self.device_action, "device_tracker")
    self.listen_event(self.receive_telegram_callback, "telegram_callback")


  def receive_telegram_callback(self, event_id, payload_event, *args):
      """Event listener for telegram callback queries."""
      assert event_id == 'telegram_callback'
      data_callback = payload_event['data']
      callback_id = payload_event['id']
      chat_id = payload_event['chat_id']
      if data_callback == "/turn_off_all_" + self.args["instance_name"]:
          for entity in self.args["entities"]:
              self.turn_off(entity)
          self.log("Turned everything off")
      else:
          self.log("Unknown telegram command received: " + str(data_callback))


  def all_not_home(self):
      """Returns True if none of the tracked users has still a device that is home."""
      for user in self.args["users"]:
          for entity in globals.users[user]["tracked_devices"]:
              if self.get_tracker_state(entity) == "home":
                  return False
          return True


  def something_on(self):
      """Returns True if the state of any device in the entity parameter list is on."""
      for entity in self.args["entities"]:
          if self.get_state(entity) == "on":
              return True
      return False


  def get_user_by_tracked_device(self, device):
      """Returns the user configuration for a given device."""
      for user in self.args["users"]:
          for tracked_device in globals.users[user]["tracked_devices"]:
              if device == tracked_device:
                  return user
      return None


  def extract_group(self, group):
      """Returns all entities of an homeassistant object. Useful for groups."""
      return self.get_state(group, attribute="all")["attributes"]["entity_id"]


  def device_action(self, entity, attribute, old, new, kwargs):
      """Callback to process device_tracker changes."""
      if old == "home" and new == "not_home":
          if self.all_not_home():
              if self.something_on():
                  # notify about online foo
                  service_name = str(self.get_user_by_tracked_device(entity)["notify"]).replace(".", "/")
                  online = []
                  for thing in self.args["entities"]:
                      for thing_2 in self.extract_group(thing):
                          if self.get_state(thing_2) == "on":
                              online.append(thing_2)
                 
                  if len(online) == 1:
                      message_content = str(self.friendly_name(online[0])) + " ist noch eingeschaltet."
                  else:
                      name_list = list(map(self.friendly_name, online))
                      message_content = ", ".join(list(name_list[:len(name_list)-1])) + " und " + name_list[len(name_list)-1] + " sind noch eingeschaltet."
                  keyboard = ["Ausschalten:/turn_off_all_" + self.args["instance_name"]]
                  self.call_service(service_name, message=message_content, data=dict(inline_keyboard=keyboard))
                  self.log("Call service " + service_name + " to send message " + message_content + " with keyboard " + str(keyboard))
