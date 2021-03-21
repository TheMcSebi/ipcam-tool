# ipcam-tool
Tool for recording IP Cameras that expose RTSP

## Requirements:
pip install numpy==1.19.3  
pip install opencv-python

## Configuration:
Configuration is done in the script's head.


```
(bool)   enabled:             if the camera is enabled during scriptn startup
(string) name:                anything to identify the camera (affects folder names)
(string) url:                 the streaming url, rtsp works, but everything cv2 supports should work too
(bool)   record_motion:       enable motion recording by default
(int)    motion_sensitivity:  min. area size of detected motion that gets recognized (smaller = more sensitive)
(bool)   record_timelapse:    enable timelapse recording by default
(int)    timelapse_speed:     only record every nth frame (timelapse records at 60fps)
(bool)   show_overlay:        show motion detection overlay for debugging and fine tuning
(bool)   update_screen:       update the gui window with frames (disable to save some cpu time)
```

Example for recording a timelapse:
```python
{
	"enabled": True,
	"name": "cam0",
	"url": "rtsp://admin:password@192.168.2.10:554/live/av0",
	"record_motion": False,
	"motion_sensitivity": 100,
	"record_timelapse": True,
	"timelapse_speed": 256,
	"show_overlay": False,
	"update_screen": False
},
```

Example for motion detection:
```python
{
	"enabled": True,
	"name": "cam1",
	"url": "rtsp://admin:password@192.168.2.11:554/live/av0",
	"record_motion": True,
	"motion_sensitivity": 100,
	"record_timelapse": False,
	"timelapse_speed": 256,
	"show_overlay": False,
	"update_screen": False
},
```

On Linux the tool doesn't show any GUI by default. 

This can be changed at the very top of the script.

## Usage:

`python3 ipcam-tool.py`

If the gui is enabled, the configuration can be controlled by keyboard input.

```
h = display this help text             
r = toggle record motion               
o = draw motion detection overlay      
u = update frame window                
t = toggle record timelapse            
+ = increase timelapse speed           
- = decrease timelapse speed           
c = print current cam configuration    
q = quit thread (works in console, too)
```

When window focus is on any of the preview windows, pressing h will print this help text.

`q` is the only key that can be used from console aswell (as of yet).

