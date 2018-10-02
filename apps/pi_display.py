import appdaemon.plugins.hass.hassapi as hass
import os

#
# App to perform stuff at the atrium display
#
# Args:
# mqtt_display_topic: topic to send new paths to
# switch_display: switch to toggle and get the state of the display
# slide_show_dir: path to the directory that holds the different picture dirs
# input_select_dir: input_select for the picture type at a slide show
# input_number_duration: input_number for single page time in minutes
# dir_reload_timer (optional): minutes to reload picture directory (defaults to 10 minutes)
#
# Version 1.0:
#   Initial Version

class PiDisplay(hass.Hass):

  def initialize(self):

    self.dirs = []
    self.current_url = None
    self.current_dir = None

    # timer to change content
    self.timer_next_page = None
    if "slide_show_dir" in self.args and "input_select_dir" in self.args:
        if "dir_reload_timer" in self.args:
            self.reload_interval = self.args["dir_reload_timer"]
        else:
            self.reload_interval = 10
        self.timer_reload_dirs = self.run_in(self.reload_dirs, self.reload_interval)
    else:
        self.log("Config not complete: slide shows are not available")

    # subscribe to controls
    if "input_select_dir" in self.args:
        self.listen_state(self.state_changed, self.args["input_select_dir"])
    else:
        self.log("No display directory input_select has been configured!")

    delay = self.get_state(self.args["input_number_duration"])
    self.timer_next_page = self.run_in(self.show_next_content, int(float(delay)))


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
      self.log("Reloading slide show dir: " + str(self.get_state(self.args["input_select_dir"])))
      self.log("Current slideshow: " + str(self.current_dir))
      self.dirs = self.get_subdirectories(self.args["slide_show_dir"])
      self.dirs.insert(0, "None")
      self.call_service(service="input_select/set_options", entity_id=self.args["input_select_dir"], options=dirs)
      self.log("Selected: " + str(self.current_dir) + "; Available: " + str(dirs))
      if self.current_dir in dirs:
          self.call_service(service="input_select/select_option", entity_id=self.args["input_select_dir"], option=self.current_dir)
          self.log("Thing.")
      else:
          self.call_service(service="input_select/select_option", entity_id=self.args["input_select_dir"], option="None")
          self.log("ERROR: DIR NOT FOUND")
      self.timer_reload_dirs = self.run_in(self.reload_dirs, self.reload_interval*10)


  def state_changed(self, entity, attribute, old, new, kwargs):
      delay = self.get_state(self.args["input_number_duration"])
      self.log("State changed, entity:" + str(entity) + " attribute: " + str(attribute))
      if str(new) != "None":
          self.log("Dir changed from " + str(old) + " to " + str(new))
          self.current_dir = new


  def show_next_content(self, kwargs):
      delay = self.get_state(self.args["input_number_duration"])
      self.timer_reload_dirs = self.run_in(self.show_next_content, int(float(delay)))
      
      if self.current_dir is None:
          return

      path = self.args["slide_show_dir"] + "/" + str(self.current_dir)
      self.log("Searching for slide shows in dir: " + str(path))
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
      else:
          self.current_url = url
          self.turn_on(self.args["switch_display"])
          self.call_service(service="mqtt/publish", topic=self.args["mqtt_display_topic"], payload=url)

