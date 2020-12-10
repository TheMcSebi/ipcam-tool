# pip install opencv-python
import cv2
import cv2 as cv
# pip install numpy==1.19.3
import numpy as np
import os
from datetime import *
import requests
from threading import Thread

#################################################################

basepath = 'C:\\cam\\'

logfile = basepath + 'log.txt'

devices = [{"name": "cam1", "url": "rtsp://user:pass@192.168.2.39:554/live/av0"},
           {"name": "cam2", "url": "rtsp://user:pass@192.168.2.41:554/live/av0"}
          ]

min_size = 100 # smaller = more sensitive; 100 = default

show_overlay_default = False
record_default = True

timelapse_capture_filter = 8 # only record every nth frame (timelapse is at 60fps)


#################################################################

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

# print menu
print("r = toggle record motion")
print("o = draw motion detection overlay")
print("u = update frame window")
print("t = record timelapse")
print("q = quit application")

# video writer
fourcc = cv2.VideoWriter_fourcc(*'DIVX')


def capture_device_thread(dev):
    global fourcc, record_default, show_overlay_default, basepath, timelapse_capture_filter
    exit_thread = False
    update_screen = True
    record = record_default
    record_timelapse = False
    show_overlay = show_overlay_default
    videopath = basepath + dev["name"] + "\\"
    
    while not exit_thread:
        log(dev["name"], "started thread")
        
        cap = cv2.VideoCapture(dev["url"])
        
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) # float
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) # float

        log(dev["name"], "video stream size: " + str(int(width)) + "x" + str(int(height)))
        log(dev["name"], "video path: " + videopath)


        out = None
        out_timelapse = None
        baseline_image = None

        current_frame = 0
        prev_frames = []

        num_frames_motion = 0
        num_frames_still = 0

        windowname = "[" + dev["name"] + "] ipcam tool"
        

        frame_with_motion = False
        framecounter = 0
        
        while(cap.isOpened()):
            ret, frame = cap.read()
            now = datetime.now()
            old_frame_with_motion = frame_with_motion
            frame_with_motion = False
            
            if ret == True:
                # copy frame to draw overlay on while displaying
                frame_original = None
                if show_overlay:
                    frame_original = frame.copy()
                
                # record timelapse frames
                if record_timelapse and ((framecounter % timelapse_capture_filter) == 0):
                    #print(framecounter)
                    if not out_timelapse:
                        file_timelapse = get_file_path(dev["name"], True)
                        if os.path.isfile(file_timelapse):
                            os.remove(file_timelapse)
                        out_timelapse = cv2.VideoWriter(file_timelapse, fourcc, 60.0, (int(width),int(height)))
                        
                        log(dev["name"], "started recording")
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
                    gray_frame = cv2.GaussianBlur(gray_frame, (25,25), 0)
                    
                    if baseline_image is None:
                        baseline_image=gray_frame
                        continue
                    
                    delta=cv2.absdiff(baseline_image, gray_frame)
                    threshold=cv2.threshold(delta, 15, 255, cv2.THRESH_BINARY)[1]
                    (contours,_)=cv2.findContours(threshold,cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    
                    for contour in contours:
                        if cv2.contourArea(contour) < min_size:
                            continue
                        
                        frame_with_motion = True
                        if show_overlay:
                            (x, y, w, h) = cv2.boundingRect(contour)
                            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 1)
                    baseline_image = gray_frame
                    
                    # draw frame if overlay is enabled (if not, draw further down)
                    if show_overlay and update_screen:
                        cv2.imshow(windowname, frame)
                
                # record if motion was detected for x frames
                if record:
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
                        # RESET EVERYTHING
                        prev_frames = []
                        if out:
                            out.release()
                            out = False
                            log(dev["name"], "stopped recording after " + str(num_frames_motion) + " frames with motion")
                        num_frames_motion = 0
                        
                    if num_frames_motion > 15:
                        # RECORD FRAMES
                        if not out:
                            file = get_file_path(dev["name"], False)
                            if os.path.isfile(file):
                                os.remove(file)
                            out = cv2.VideoWriter(file, fourcc, 20.0, (int(width),int(height)))
                            
                            log(dev["name"], "started recording")
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
                record = not record
                log(dev["name"], "record = " + str(record))
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

        # quit capturing device
        cap.release()

        # quit timelapse recording if enabled
        if out_timelapse:
            log(dev["name"], "timelapse ended")
            out_timelapse.release()
        
        # quit motion recording if enabled
        if out:
            out.release()
            log(dev["name"], "thread exited")

        #cv2.destroyAllWindows()
        
        cv2.destroyWindow(windowname)
        log(dev["name"], "thread exited")

for dev in devices:
    t = Thread(target=capture_device_thread, args=(dev,))
    t.start()