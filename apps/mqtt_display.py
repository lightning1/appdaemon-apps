import appdaemon.plugins.hass.hassapi as hass
import os

#
# App to display stuff on a remote controlled display
#   Note: the display needs some mechanism to show URLs send via mqtt
#
# Args:
# mqtt_display_topic_file: topic to send new local paths to
# mqtt_display_topic_url: topic to send URLs to
# instance_name: name of the display, has to be unique
#
# Optional Ars:
# switch_display: switch(es) to toggle and get the state of the displays power supply
# slide_show_dir: path to the directory that holds the different picture dirs
# input_number_duration: input_number for display time in seconds (defaults to 60)
#    Warning: do not use really small values if your mqtt display can not handle fast changes!
# dir_reload_timer: minutes to reload slide show base directory (defaults to 10 minutes)
# dir_sensor_name: sensor to display the current display state
#
# Version 1.0:
#   Initial Version
# Version 2.0:
#   Instant changes (correct timer usage)
#   Handle external image sources (from other apps)


class MqttDisplay(hass.Hass):

  def initialize(self):
    self.show_external_image = False
    # cache for urls send by other apps
    self.external_images = []
    self.dirs = []
    self.current_url = None
    self.current_dir = None
    self.display_duration = None
    # possible modes:
    #   None: display is turned off
    #   slideshow: showing an slideshow
    #   url: showing an url by an external service
    self.mode = None

    # timers
    self.timer_slideshow_next = None
    self.timer_reload_dirs = None

    if "instance_name" not in self.args:
        self.log("No instance name configured! This is necessary for interacting with other apps like telegram_bot.")
    if "slide_show_dir" in self.args:
        if "dir_reload_timer" in self.args:
            self.reload_interval = self.args["dir_reload_timer"]
        else:
            self.reload_interval = 10
        self.timer_reload_dirs = self.run_in(self.reload_dirs, self.reload_interval)
        self.log("Setup dir reloading...")
    else:
        self.log("Config not complete: slide shows are not available")


  def turn_off_display(self):
    self.mode = None
    self.cancel_timer(self.timer_slideshow_next)
    self.log("Turning off display")
    if "dir_sensor_name" in self.args:
        self.set_state(self.args["dir_sensor_name"], state="Aus", attributes={"friendly_name": "Status", "icon": "mdi:monitor"})
    if type(self.args["switch_display"]) is list:
        for switch in self.args["switch_display"]:
            self.turn_off(switch)
    elif "switch_display" in self.args:
        self.turn_off(self.args["switch_display"])


  def turn_on_display(self):
    self.log("Turning on display")
    if "dir_sensor_name" in self.args:
        self.set_state(self.args["dir_sensor_name"], state="An", attributes={"friendly_name": "Status", "icon": "mdi:monitor"})
    if type(self.args["switch_display"]) is list:
        for switch in self.args["switch_display"]:
            self.turn_on(switch)
    elif "switch_display" in self.args:
        self.turn_on(self.args["switch_display"])


  def slideshow_start(self, directory):
        self.mode = "slideshow"
        if "dir_sensor_name" in self.args:
            self.set_state(self.args["dir_sensor_name"], state="Slideshow: " + str(self.current_dir), attributes={"friendly_name": "Status", "icon": "mdi:filmstrip"})
        self.cancel_timer(self.timer_slideshow_next)
        self.current_dir = directory
        self.show_next_content()


  def get_external_images_size(self):
      """Returns the size of the queue for URLs, counts plus one if an URL is displayed right now."""
      if self.show_external_image:
          return len(self.external_images) + 1
      else:
          return len(self.external_images)


  def get_display_duration(self):
      if "input_number_duration" in self.args:
          return self.get_state(self.args["input_number_duration"])
      else:
          return 60


  def show_url(self, url, icon="mdi:image", source=None, user=None):
      """Adds a given URL to the queue. The optional arguments are used to improve the display sensor state."""
      delay = self.get_display_duration()
      if self.mode is None:
          self.turn_on_display()
          self.mode = "url"
      if source is None and user is None:
          status_message = "URL wird angezeigt"
      elif source is None:
          status_message = "URL von " + str(user)
      elif user is None:
          status_message = "URL aus " + str(source)
      else:
          status_message = "URL von " + str(user) + " über " + str(source)
      image_dict = {"url": url,
                    "icon": icon,
                    "message": status_message}
      self.external_images.insert(0, image_dict)
      self.log("Added external URL to queue: " + str(image_dict))
      if self.mode == "slideshow" and len(self.external_images) == 1:
          self.cancel_timer(self.timer_slideshow_next)
          self.show_next_content()
      elif self.mode == "url" and len(self.external_images) == 1 and not self.show_external_image:
          self.show_next_content()


  def get_subdirectories(self, a_dir):
      if os.path.isdir(a_dir):
          subdirs = []
          for name in os.listdir(a_dir):
              if os.path.isdir(os.path.join(a_dir, name)):
                  subdirs.append(name)
          return subdirs
      else:
          return []


  def reload_dirs(self, kwargs):
      """Periodically reloads the possible slide shows from the filesystem."""
      self.log("Reloading slide show dir: " + str(self.args["slide_show_dir"]))
      self.dirs = self.get_subdirectories(self.args["slide_show_dir"])
      self.dirs.insert(0, "None")
      if self.current_dir not in self.dirs and self.current_dir is not None:
          self.log("Directory " + str(self.current_dir) + " not found, internal state error")
      self.timer_reload_dirs = self.run_in(self.reload_dirs, self.reload_interval*10)


  def show_next_content(self, kwargs=None):
      """Shows the next URL or image. If the queue contains elements, those are presented before a slideshow."""
      delay = self.get_display_duration()
      cancel_timer = False
      self.show_external_image = False
     
      # determinate if slideshow or url display 
      if len(self.external_images) > 0:
          image = self.external_images.pop()
          self.call_service(service="mqtt/publish", topic=self.args["mqtt_display_topic_url"], payload=image["url"])
          if "dir_sensor_name" in self.args:
              self.set_state(self.args["dir_sensor_name"], state=image["message"], attributes={"friendly_name": "Status", "icon": image["icon"]})
          self.show_external_image = True
      else:
          path = self.args["slide_show_dir"] + "/" + str(self.current_dir)
          self.log("Searching for pictures in dir: " + str(path))
          pictures = []
          for root, dirs, files in os.walk(path):  
              for filename in files:
                  pictures.append(path + "/" + filename)
          if self.current_url in pictures:
              prev_pos = pictures.index(self.current_url)
              if len(pictures) > prev_pos + 1:
                  # next picture can be displayed
                  url = pictures[prev_pos + 1]
              else:
                  url = pictures[0]
          elif len(pictures) > 0:
              url = pictures[0]
          else:
              url = None
          self.log("Show next picture in slideshow: " + str(url))
          if url is None:
              # no picture available!
              self.log("No pictures to show, terminating the slide show")
              cancel_timer = True
          else:
              self.current_url = url
              self.call_service(service="mqtt/publish", topic=self.args["mqtt_display_topic_file"], payload=url)
              if "dir_sensor_name" in self.args:
                  self.set_state(self.args["dir_sensor_name"], state="Slideshow: " + str(self.current_dir), attributes={"friendly_name": "Status", "icon": "mdi:filmstrip"})
      # timer stuff
      if (self.mode == "slideshow" or len(self.external_images) > 0) and not cancel_timer:
          self.timer_slideshow_next = self.run_in(self.show_next_content, int(float(delay)))
