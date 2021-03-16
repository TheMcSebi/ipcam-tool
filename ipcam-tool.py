# pip install opencv-python
import cv2
import cv2 as cv
# pip install numpy==1.19.3
import numpy as np
import os
from datetime import *
import requests
from threading import Thread

debug = False

#################################################################

basepath = 'H:\\cam\\'

logfile = basepath + 'log.txt'

win_w = 768
win_h = 432 # 1080p / 2.5

fps_default = 25.0

# an array of 8 key-value pairs for each camera instance
# (string) name:                anything to identify the camera (affects folder and file names)
# (string) url:                 the streaming url, rtsp works, but everything cv2 supports should work too
# (bool)   record_motion:       enable motion recording by default
# (int)    motion_sensitivity:  min. area size of detected motion that gets recognized (smaller = more sensitive)
# (bool)   record_timelapse:    enable timelapse recording by default
# (int)    timelapse_speed:     only record every nth frame (timelapse records at 60fps)
# (bool)   show_overlay:        if motion detection is shown in the window
# (bool)   update_screen:       if the desktop window is updated
devices = [
    {
        "enabled": True,
        "name": "cam0", 
        "url": "rtsp://admin:password@192.168.2.10:554/live/av0", 
        "record_motion": False, 
        "motion_sensitivity": 100, 
        "record_timelapse": False, 
        "timelapse_speed": 16, 
        "show_overlay": False, 
        "update_screen": True
    },
    {
        "enabled": True,
        "name": "cam1", 
        "url": "rtsp://admin:password@192.168.2.11:554/live/av0", 
        "record_motion": False, 
        "motion_sensitivity": 100, 
        "record_timelapse": False, 
        "timelapse_speed": 16, 
        "show_overlay": False, 
        "update_screen": True
    },
]

#################################################################

def display_help():
    print("##########################################")
    print("# h = display this help text             #")
    print("# r = toggle record motion               #")
    print("# o = draw motion detection overlay      #")
    print("# u = update frame window                #")
    print("# t = toggle record timelapse            #")
    print("# + = increase timelapse speed           #")
    print("# - = decrease timelapse speed           #")
    print("# c = print current cam configuration    #")
    print("# q = quit application                   #")
    print("##########################################")

# log timestamp, threadname and any string to file and display on screen
def log(name, logstr):
    global logfile
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    msg = timestamp + "> [" + name + "] " + logstr
    print(msg)
    with open(logfile, "a") as myfile:
        myfile.write(msg + "\n")

def get_file_path(name, record_timelapse):
    global basepath
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    pathstring = basepath + name + "\\" + timestamp
    if record_timelapse:
        pathstring = pathstring + "-timelapse"
    return pathstring + ".avi"


log("application", "started")
log("application", "log file: " + logfile)

display_help()

# set up video writer
# for details see https://docs.opencv.org/master/dd/d43/tutorial_py_video_display.html#nav-path:~:text=Saving%20a%20Video
fourcc = cv2.VideoWriter_fourcc(*'DIVX')

def capture_device_thread(dev, index):
    log(dev["name"], "started thread " + str(index))
    global fourcc, basepath, win_w, win_h, fps_default

    exit_thread = False
    update_screen = dev["update_screen"]
    record_motion = dev["record_motion"]
    motion_sensitivity = dev["motion_sensitivity"]
    record_timelapse = dev["record_timelapse"]
    timelapse_speed = dev["timelapse_speed"]>>1
    show_overlay = dev["show_overlay"]
    videopath = basepath + dev["name"] + "\\"
    windowname = "[" + dev["name"] + "] ipcam tool"
    fps = fps_default
    
    log(dev["name"], ("settings:" + 
        " update_screen=" + str(update_screen) + 
        " record_motion=" + str(record_motion) + 
        " motion_sensitivity=" + str(motion_sensitivity) + 
        " record_timelapse=" + str(record_timelapse) + 
        " timelapse_speed=" + str(timelapse_speed) + 
        " show_overlay=" + str(show_overlay) + 
        " videopath=" + videopath + 
        " windowname=" + windowname + 
        " fps=" + str(fps))
    )
    
    
    if debug:
        update_screen = True
        record_motion = False
        record_timelapse = False
        show_overlay = True
        windowname = windowname + " (debug)"
    
    log(dev["name"], "video path: " + videopath)
    
    # check if there's a directory for this camera already
    if not os.path.isdir(basepath + dev["name"]):
        os.mkdir(basepath + dev["name"])
        log(dev["name"], "video path didn't exist and was created")
    
    if not os.path.isdir(basepath + dev["name"] + "\\timelapse"):
        os.mkdir(basepath + dev["name"] + "\\timelapse")
        log(dev["name"], "timelapse path didn't exist and was created")
        
    out = None
    out_timelapse = None
    baseline_image = None
    prev_frames = []
    num_frames_motion = 0
    num_frames_still = 0
    framecounter = 0

    while not exit_thread:
        if cv2.getWindowProperty('window-name', 0) == -1:
            cv2.namedWindow(windowname, cv2.WINDOW_NORMAL)
            
            cv2.resizeWindow(windowname, win_w, win_h)
            
            # get correct window position
            win_x = int(((index//4)*2 + index%2) * win_w)
            win_y = int(((index//2) % 2) * win_h * 1.07)
            
            cv2.moveWindow(windowname, win_x, win_y)
            
            log(dev["name"], "preview window opened at " + str(win_x) + "/" + str(win_y))
        
        cap = cv2.VideoCapture(dev["url"])
        
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) # float
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) # float
        if cap.get(cv2.CAP_PROP_FPS) > 0 and cap.get(cv2.CAP_PROP_FPS) <= 60: # failsafe
            fps = cap.get(cv2.CAP_PROP_FPS) # float

        log(dev["name"], "video stream opened: " + str(int(width)) + "x" + str(int(height)) + "@" + str(int(fps)) + "fps")

        frame_with_motion = False
        
        while(cap.isOpened()):
            ret, frame = cap.read()
            old_frame_with_motion = frame_with_motion
            frame_with_motion = False
            
            # if the video gets interrupted for some reason, the capture device will be reinitiated
            if ret == True:
                # copy frame to draw overlay on while displaying
                frame_original = None
                if show_overlay:
                    frame_original = frame.copy()
                
                # record timelapse frames
                if record_timelapse and ((framecounter % timelapse_speed) == 0):
                    #print(framecounter)
                    if not out_timelapse:
                        file_timelapse = get_file_path(dev["name"] + "\\timelapse", True)
                        if os.path.isfile(file_timelapse):
                            os.remove(file_timelapse)
                        out_timelapse = cv2.VideoWriter(file_timelapse, fourcc, 60.0, (int(width),int(height)))
                        
                        log(dev["name"], "started recording timelapse")
                        log(dev["name"], "writing to " + file_timelapse)
                    else:
                        if show_overlay:
                            out_timelapse.write(frame_original)
                        else:
                            out_timelapse.write(frame)
                
                # do motion detection every second frame
                if framecounter % 2 == 0:
                    gray_frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
                    gray_frame = cv2.resize(gray_frame, (640,360), interpolation = cv2.INTER_LINEAR)
                    scale_factor = int(width/640)
                    gray_frame = cv2.GaussianBlur(gray_frame, (25,25), 0)
                    
                    if baseline_image is None:
                        baseline_image=gray_frame
                        continue
                    
                    delta=cv2.absdiff(baseline_image, gray_frame)
                    threshold=cv2.threshold(delta, 15, 255, cv2.THRESH_BINARY)[1]
                    (contours,_)=cv2.findContours(threshold,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    
                    for contour in contours:
                        if cv2.contourArea(contour) < motion_sensitivity:
                            continue
                        
                        frame_with_motion = True
                        if show_overlay:
                            (x, y, w, h) = cv2.boundingRect(contour)
                            cv2.rectangle(frame, (x*scale_factor, y*scale_factor), (x*scale_factor + w*scale_factor, y*scale_factor + h*scale_factor), (0,255,0), 1)
                    
                    baseline_image = gray_frame
                    
                    # draw frame if overlay is enabled (if not, draw further down)
                    if show_overlay and update_screen:
                        cv2.imshow(windowname, frame)
                
                # record if motion was detected for x frames
                if record_motion:
                    if frame_with_motion or old_frame_with_motion:
                        if show_overlay:
                            prev_frames.append(frame_original)
                        else:
                            prev_frames.append(frame)
                        
                        num_frames_motion = num_frames_motion + 1
                        num_frames_still = 0
                    else:
                        num_frames_still = num_frames_still + 1
                    
                    if num_frames_still >= 90:
                        # reset recording
                        prev_frames = []
                        if out:
                            out.release()
                            out = False
                            log(dev["name"], "stopped recording motion after " + str(num_frames_motion) + " frames with motion (" + str(int(num_frames_motion/fps)) + "s)")
                        num_frames_motion = 0
                        
                    if num_frames_motion > 15:
                        # save frame
                        if not out:
                            file = get_file_path(dev["name"], False)
                            if os.path.isfile(file):
                                os.remove(file)
                            out = cv2.VideoWriter(file, fourcc, 20.0, (int(width),int(height)))
                            
                            log(dev["name"], "started recording motion")
                            log(dev["name"], "writing to " + file)
                            
                            for f in prev_frames:
                                out.write(f)
                        else:
                            if show_overlay:
                                out.write(frame_original)
                            else:
                                out.write(frame)
                
                # draw frame if the overlay is disabled
                if not show_overlay and update_screen:
                    cv2.imshow(windowname, frame)
            
            else:
                break
            
            framecounter = framecounter + 1
            # read key if pressed
            key = cv2.waitKey(20) & 0xFF
            
            # query keys
            if key == ord('q'): # quit
                log(dev["name"], "thread stopped")
                exit_thread = True
                break
                
            elif key == ord('r'): # record motion
                record_motion = not record_motion
                log(dev["name"], "record_motion = " + str(record_motion))
                if out:
                    out.release()
                    out = None
                    log(dev["name"], "motion recording ended")
                
            elif key == ord('o'): # show motion detection overlay
                show_overlay = not show_overlay
                log(dev["name"], "show_overlay = " + str(show_overlay))
                
            elif key == ord('u'): # show every frame in a window
                update_screen = not update_screen
                log(dev["name"], "update_screen = " + str(update_screen))
                
            elif key == ord('t'): # record timelapse
                record_timelapse = not record_timelapse
                log(dev["name"], "record_timelapse = " + str(record_timelapse))
                
                if out_timelapse:
                    log(dev["name"], "timelapse ended")
                    out_timelapse.release()
                    out_timelapse = None
                else:
                    log(dev["name"], "timelapse_speed = " + str(timelapse_speed << 1) + "x")
                    
            elif key == ord('-'): # timelapse speed slower
                if timelapse_speed >> 1 > 0:
                    timelapse_speed = timelapse_speed >> 1
                log(dev["name"], "timelapse_speed = " + str(timelapse_speed << 1) + "x")
                
            elif key == ord('+'): # timelapse speed faster
                timelapse_speed = timelapse_speed << 1
                log(dev["name"], "timelapse_speed = " + str(timelapse_speed << 1) + "x")
            
            elif key == ord('c'): # display help message
                log(dev["name"], "record_motion = " + str(record_motion))
                log(dev["name"], "show_overlay = " + str(show_overlay))
                log(dev["name"], "update_screen = " + str(update_screen))
                log(dev["name"], "record_timelapse = " + str(record_timelapse))
                log(dev["name"], "timelapse_speed = " + str(timelapse_speed << 1) + "x")
            
            elif key == ord('h'): # display help message
                display_help()

        # quit capturing device
        cap.release()
        log(dev["name"], "capture device closed")

    # quit timelapse recording if enabled
    if out_timelapse:
        out_timelapse.release()
        log(dev["name"], "timelapse ended")
    
    # quit motion recording if enabled
    if out:
        out.release()
        log(dev["name"], "motion recording ended")

    #cv2.destroyAllWindows()
    
    cv2.destroyWindow(windowname)
    log(dev["name"], "thread exited")

index = 0
for dev in devices:
    if dev["enabled"]:
        t = Thread(target=capture_device_thread, args=(dev,index,))
        t.start()
        index = index + 1