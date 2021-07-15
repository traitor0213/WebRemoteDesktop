from PIL import ImageGrab

import io
import socket
import threading
import base64
import time
import pyautogui
import random

from urllib import parse

pyautogui.FAILSAFE = False

userIdList = []
screenshotList = []
imageBytes = None
image = ImageGrab.grab()

screenCaptureServiceStop = False
def screenCaptureService():
    global screenCaptureServiceStop
    global imageBytes
    while True:
        if screenCaptureServiceStop == True:
            break 

        if len(userIdList) != 0:
            image = ImageGrab.grab()
            _imageBytes = io.BytesIO()
            image.save(_imageBytes, format='JPEG')
            imageBytes = _imageBytes.getvalue()

        time.sleep(0.1)

keyList = [
    "ctrl",
    "shift",
    "win",
    "right",
    "left",
    "up",
    "left",
]

keyReplaceMap = [
    {"Control": "ctrl"},
    {"Shift": "shift"},
    {"Meta": "win"},
    {"ArrowRight": "right"},
    {"ArrowLeft": "left"},
    {"ArrowUp": "up"},
    {"ArrowDown": "down"},
]

keyStatusMap = []


keyStatusManagerStop = False 
def keyStatusManager():
    global keyStatusMap
    global keyStatusManagerStop

    while True:
        time.sleep(3)
        
        if keyStatusManagerStop == True:
            break 

        currentNs = time.perf_counter_ns()

        for keyStatus in keyStatusMap:
            if (currentNs - keyStatus["ns"]) > 1000000000:
                print("timeout to keyup:", keyStatus["key"])
                
                try:
                    pyautogui.keyUp(keyStatus["key"])
                    keyStatusMap.remove(keyStatus)
                except:
                    pass

clientIOThreadList = []

clientIOManagerStop = False
def clientIOManager():
    global clientIOManagerStop
    global clientIOThreadList

    while True:
        if clientIOManagerStop == True:
            break 

        for clientIOThread in clientIOThreadList:            
            if (time.perf_counter_ns() - clientIOThread["ns"]) > 3000000000:
                try:
                    clientIOThread["socket"].shutdown(socket.SHUT_RDWR)
                    clientIOThread["socket"].close()
                except:
                    pass 

                clientIOThreadList.remove(clientIOThread)

        time.sleep(3)

    return

def createHttpResponse(body, contentType="text"):
    bodyLength = len(body)
    httpResponseHeader = ("HTTP/1.1 200 OK\r\n"
        "Connection: close\r\n" 
        "Content-Type: %s\r\n" 
        "Access-Control-Allow-Origin:*\r\n"  
        "Content-Length: %d\r\n\r\n" % ( 
        contentType, 
        bodyLength)
    )
    
    if type(body) == str:
        body = body.encode()

    httpResponseHeader = httpResponseHeader.encode()
    httpResponseHeader += body

    return httpResponseHeader

def checkUser(requestPath):
    global userIdList
    existUserId = False
    for userId in userIdList:
        if "/?userId=" + userId in requestPath:
            existUserId = True

    return existUserId

def clientIOSubRoutine(requestPath):
    global imageBytes
    global userIdList
    global image
    global screenshotList

    if "/createUser" in requestPath:
        userId = str(time.perf_counter_ns())
        userIdList.append(userId)

        return createHttpResponse(userId)

    if "/deleteUser" in requestPath:
        if checkUser(requestPath) == True:
            userIdList.remove(existUserId)

    if "/mousing" in requestPath:
        if checkUser(requestPath) == True:
            if "x=" in requestPath and "y=" in requestPath:
                clientX = requestPath.split("x=")[1].split(";")[0]
                clientY = requestPath.split("y=")[1].split(";")[0]

                try:
                    pyautogui.moveTo(int(clientX), int(clientY))
                except:
                    pass 

    if "/getScreenSize" in requestPath:
        (x, y) = pyautogui.size()
        return createHttpResponse(str(x) + "," + str(y))
    
    if "/mouseWhell" in requestPath:
        if checkUser(requestPath):
            y = requestPath.split("y=")[1].split(";")[0]
            pyautogui.scroll(int(y))

    if "/mouseDown" in requestPath:
        if checkUser(requestPath):
            try:
                pyautogui.mouseDown()
            except:
                pass

    if "/mouseUp" in requestPath:
        if checkUser(requestPath):
            try:
                pyautogui.mouseUp()
            except:
                pass 

    if "/mouseRightClick" in requestPath:
        if checkUser(requestPath):
            pyautogui.click(button='right')

    if "/keyboarding" in requestPath:
        if checkUser(requestPath) == True:
            if "key=" in requestPath:
                key = requestPath.split("key=")[1].split("&")[0]

                if type(key) != str:
                    return createHttpResponse("remote desktop error page")

                for keyReplace in keyReplaceMap:
                    try: 
                        key = keyReplace[key]
                        break 
                    except:
                        pass 

                key = parse.unquote(key)

                if "keydown=true" in requestPath:
                    try:
                        pyautogui.keyDown(key)
                    except:
                        pass

                    for userId in userIdList:
                        if "/?userId=" + userId in requestPath:
                            break

                    if {key: "down"} not in keyStatusMap: 
                        keyStatusMap.append({"key": key, key: "down", "ns":time.perf_counter_ns(), "userId":userId})
                else:
                    for keyStatus in keyStatusMap:
                        if keyStatus["key"] == key:
                            keyStatusMap.remove(keyStatus)

                    try:
                        pyautogui.keyUp(key)
                    except:
                        pass

    if "/getMonitorBuffer/" in requestPath:
        if checkUser(requestPath) == True:
            if imageBytes != None:
                body = base64.b64encode(imageBytes)
                beforeMonitor = body

                return createHttpResponse(body)
        else:
            return createHttpResponse("error: unregistered ID")

    if "/screenshotRouter2/" in requestPath:
        if checkUser(requestPath) == True:
            if imageBytes != None:
                return createHttpResponse(imageBytes, contentType="image/jpeg")

    if "/screenshotId/" in requestPath:
        if checkUser(requestPath) == True:

            # append to list
            """
            "/screenshotRouter/" + str(time.perf_counter_ns())
            """

            screenshotInfo = {"imageFile": imageBytes, "routeTo":str(time.perf_counter_ns())}
            screenshotList.append(screenshotInfo)

            return createHttpResponse(screenshotInfo["routeTo"])
        else:
            return createHttpResponse("error: unregistered ID")

    for screenshotInfo in screenshotList:
        if checkUser(requestPath) == True:
            if "/screenshotRouter/" + screenshotInfo["routeTo"] in requestPath:
                body = createHttpResponse(screenshotInfo["imageFile"], contentType="image/jpeg")
                screenshotList.remove(screenshotInfo)
                return body    

    return createHttpResponse("")

def clientIO(clientSocket: socket.socket):
    global keyStatusMap
    global userList 
    httpRequestHeader = ""

    while True:
        recvedByte = clientSocket.recv(1)
        
        httpRequestHeader += recvedByte.decode('utf-8')

        if "\r\n\r\n" in httpRequestHeader:
            break 

    requestMethod = httpRequestHeader.split(" ")[0]
    requestPath = httpRequestHeader.split(" ")[1].split(" ")[0]

    httpResponse = clientIOSubRoutine(requestPath)

    clientSocket.send(httpResponse)
    clientSocket.shutdown(socket.SHUT_RDWR)
    clientSocket.close()

    return

def init() -> socket.socket:
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.setblocking(False)
    serverSocket.bind(("", 9000))
    serverSocket.listen(20)

    return serverSocket 

def main():
    threading.Thread(target=keyStatusManager).start()
    threading.Thread(target=screenCaptureService).start()
    threading.Thread(target=clientIOManager).start()
    
    serverSocket = init()
    
    global clientIOThreadList

    while True:
        try:
            (clientSocket, clientAddress) = serverSocket.accept()
            clientSocket.setblocking(True)
            clientIOThread = threading.Thread(target=clientIO, args=(clientSocket, ))
            
            clientIOThreadList.append({"socket": clientSocket, "ns": time.perf_counter_ns()})
            clientIOThread.start()
        except:
            time.sleep(0)
            pass 

    return 

if __name__ == "__main__":
    main()