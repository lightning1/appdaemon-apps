import appdaemon.plugins.hass.hassapi as hass
import globals
import re

#
# App to manage remote control of various HA services via telegram
#
# Currently supports:
#   mqtt_display instances to activate slide shows or display URLs send via private telegram messages
#
# To use this a global configuration file is required.
#
# Args:
# displays (optional): list of appdaemon instances of mqtt_display
#
# Version 1.0:
#   Initial Version

class TelegramBot(hass.Hass):

  def initialize(self):
      self.listen_event(self.receive_telegram_callback, "telegram_callback")
      self.listen_event(self.receive_telegram_text, "telegram_text")
      self.show_url_cache = []


  def handle_show_url(self, target, display=None, url=None, username=None):
      """Shows URLs on an display (requires an instance of mqtt_display app)."""
      if url is not None and len(url) > 0:
          cache_entry = next((x for x in self.show_url_cache if x["target"] == target), None)
          if cache_entry is not None:
              self.show_url_cache.remove(cache_entry)
          self.show_url_cache.append({"url" : url, "target": target, "username": username})
      else:
          for u in self.show_url_cache:
              if u["target"] == target:
                  url = u["url"]
                  username = u["username"]
      display_apps = []
      for displays in self.args["displays"]:
          display_apps.append(self.get_app(displays))
      if len(display_apps) > 0:
          # match display
          matched_display = next((x for x in display_apps if x.args["instance_name"] == display), None)
      if matched_display is None:
          # ask for display to send URL to
          if len(display_apps) == 1:
              # no display chooser necessary, because there is only one display
              self.handle_show_url(target=target, display=display_apps[0].args["instance_name"], url=url, username=username)
          else:
              message_content = "Wähle ein Anzeigegerät:"
              keyboard = []
              for app in display_apps:
                  display_name = app.args["instance_name"]
                  keyboard.append(display_name + ":/show_url;" + display_name)
              self.call_service("telegram_bot/send_message", message=message_content, target=target, inline_keyboard=keyboard)
      else:
          matched_display.show_url(url=url, icon="mdi:telegram", source="Telegram", user=username)
          msg = "Die URL wurde der Warteschlange für " + str(matched_display.args["instance_name"]) + " hinzugefügt. Die Warteschlange enthält nun "
          if matched_display.get_external_images_size() == 1:
              msg += "einen Eintrag."
          else:
              msg += str(matched_display.get_external_images_size()) + " Einträge."
          self.call_service("telegram_bot/send_message", message=msg, target=target)


  def handle_slideshow(self, target, display=None, action=None, params=None):
      """All telegram slide show commands are controlled here."""
      display_apps = []
      for displays in self.args["displays"]:
          display_apps.append(self.get_app(displays))
      if len(display_apps) > 0:
          # match display
          matched_display = next((x for x in display_apps if x.args["instance_name"] == display), None)
          if matched_display is not None or action is None:
              if action == "select_display" or action is None:
                  if len(display_apps) == 1:
                      # no display chooser necessary, because there is only one display
                      self.handle_slideshow(target=target, display=display_apps[0].args["instance_name"], action="choose_dir")
                  else:
                      message_content = "Wähle ein Anzeigegerät:"
                      keyboard = []
                      for app in display_apps:
                          display_name = app.args["instance_name"]
                          keyboard.append(display_name + ":/slideshow;" + display_name + ";choose_dir")
                      self.call_service("telegram_bot/send_message", message=message_content, target=target, inline_keyboard=keyboard)
              elif action == "choose_dir":
                  if matched_display.mode is None:
                      message_content = "Wähle eine Slideshow"
                  elif matched_display.mode == "slideshow":
                      message_content = "Aktuelle Slideshow: " + matched_display.current_dir
                  else:
                      message_content = "Wähle eine Slideshow die angezeigt wird, nachdem die aktuellen Bilder abgearbeitet wurden"
                  keyboard = []
                  options = []
                  for d in matched_display.dirs:
                      if str(d) == "None":
                          if matched_display.current_dir is not None:
                              keyboard.append("Ausschalten:/slideshow;" + matched_display.args["instance_name"] + ";turn_off")
                      else:
                          if matched_display.current_dir != d:
                              options.append(d + ":/slideshow;" + matched_display.args["instance_name"] + ";change_dir;" + d)
                  while len(options) > 2:
                      keyboard.append(options.pop() + "," + options.pop() + "," + options.pop())
                  if len(options) == 2:
                      keyboard.append(options.pop() + "," + options.pop())
                  if len(options) == 1:
                      keyboard.append(options.pop())
                  self.call_service("telegram_bot/send_message", message=message_content, target=target, inline_keyboard=keyboard)
                  self.log("Send telegram message " + message_content + " with keyboard " + str(keyboard))
        
              elif action == "turn_off":
                  matched_display.current_dir = None
                  self.call_service("telegram_bot/send_message", message="Slideshow ausgeschaltet.", target=target)
                  matched_display.turn_off_display()
              elif action == "change_dir":
                  matched_display.slideshow_start(params[0])
                  self.call_service("telegram_bot/send_message", message="Slideshow " + matched_display.current_dir + " auf " + matched_display.args["instance_name"] + " gestartet.", target=target)
                  matched_display.turn_on_display()
              else:
                self.log("Unknown telegram action for this app received: " + str(action))
          else:
              self.log("The display " + str(display) + " could not be matched to a registered display!")


  def receive_telegram_callback(self, event_id, payload_event, *args):
      """Event listener for telegram callback queries."""
      assert event_id == 'telegram_callback'
      params = payload_event['data'].replace("/","").split(";")
      if len(params) > 0:
          if len(params) > 2 and params[0] == "slideshow":
              self.handle_slideshow(target=payload_event["chat_id"], display=params[1], action=params[2], params=params[3:])
          elif params[0] == "show_url":
              self.handle_show_url(target=payload_event["chat_id"], display=params[1])
          else:
              self.log("Unknown telegram callback received: " + str(data_callback))
      else:
          self.log("Malformed telegram callback received: " + str(data_callback))


  def receive_telegram_text(self, event_id, payload_event, *args):
      """Event listener for telegram text queries."""
      assert event_id == 'telegram_text'
      data_message = payload_event['text']
      regex = re.compile(
              r'^(?:http|ftp)s?://' # http:// or https://
              r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
              r'localhost|' #localhost...
              r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
              r'(?::\d+)?' # optional port
              r'(?:/?|[/?]\S+)$', re.IGNORECASE)
      if re.match(regex, data_message):
	  # its an URL!
          # display it at a screen
          self.handle_show_url(target=payload_event['chat_id'], url=data_message, username=payload_event["from_first"])
      else:
          # not an URL.
          # starting slideshow dialog
          self.handle_slideshow(target=payload_event['chat_id'])
