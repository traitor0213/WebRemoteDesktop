# this code is writed for python 3.8

from PIL import ImageGrab

import os
import io

import socket
import select

import threading
import base64
import time
import pyautogui
import random

from urllib import parse
import screeninfo

pyautogui.FAILSAFE = False

userInfoList = []

def getScreenCapture(monitorIndex: int):
    try:
        monitor = screeninfo.get_monitors()[monitorIndex]
        image = ImageGrab.grab(all_screens=True)

        xPlus = monitor.x
        yPlus = monitor.y

        image = image.crop([monitor.x, monitor.y, monitor.width + xPlus, monitor.height + yPlus])
        _imageBytes = io.BytesIO()
        image.save(_imageBytes, format='JPEG')
        imageBytes = _imageBytes.getvalue()

        return imageBytes
    except:
        return None

def getScreenPosition(monitorIndex: int):
    try:
        monitor = screeninfo.get_monitors()[monitorIndex]
    except:
        return None

    xPlus = monitor.x
    yPlus = monitor.y

    return [xPlus, yPlus]


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
    {"Alt": "alt"},
    {"Meta": "win"},
    {"ArrowRight": "right"},
    {"ArrowLeft": "left"},
    {"ArrowUp": "up"},
    {"ArrowDown": "down"},
]

keyStatusMap = []


keyStatusManagerStop = False 
def userStatusManager():
    global userInfoList
    global keyStatusMap
    global keyStatusManagerStop

    while True:
        time.sleep(10)
        
        if keyStatusManagerStop == True:
            break 

        currentNs = time.perf_counter_ns()

        userInfoIndex = 0
        for userInfo in userInfoList:
            if (currentNs - userInfo["last-connection"]) > 1000000000:
                print("# delete user: " + userInfo["userId"])
                print("# reason: connection timeout")
                
                # key release
                for keyStatus in keyStatusMap:
                    pyautogui.keyUp(keyStatus["key"])

                userInfoList.remove(userInfo)

            userInfoIndex += 1


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
    global userInfoList
    existUserId = False
    userInfoIndex = 0
    for userInfo in userInfoList:
        if "/?userId=" + userInfo["userId"] in requestPath:
            userInfo["last-connection"] = time.perf_counter_ns()
            userInfoList[userInfoIndex] = userInfo 
            existUserId = True
        
        userInfoIndex += 1
 

    return existUserId

def getScreenIndex(requestPath):
    if "&screenIndex=" in requestPath:
        return int(requestPath.split("&screenIndex=")[1].split(";")[0])


def clientIOSubRoutine(requestPath):
    global userInfoList

    if "/remote-desktop" in requestPath:
        print(os.getcwd() + "/remote-desktop.html")
        
        f = open(os.getcwd() + "/remote-desktop.html", "r")
        body = f.read()
        f.close()

        return createHttpResponse(body)

    if "/createUser" in requestPath:
        userId = str(time.perf_counter_ns())
        userInfo = {"userId": userId, "last-connection": time.perf_counter_ns()}

        print("# create user: " + userInfo["userId"])

        userInfoList.append(userInfo)

        return createHttpResponse(userId)

    if "/deleteUser" in requestPath:
        if checkUser(requestPath) == True:
            userInfoList.remove(existUserId)

    if "/mousing" in requestPath:
        if checkUser(requestPath) == True:
            if "x=" in requestPath and "y=" in requestPath:
                clientX = requestPath.split("x=")[1].split(";")[0]
                clientY = requestPath.split("y=")[1].split(";")[0]
                screenIndex = getScreenIndex(requestPath)
                if screenIndex != None:
                    
                    try:
                        (xPlus, yPlus) = getScreenPosition(screenIndex)
                        threading.Thread(target=pyautogui.moveTo, args=(int(clientX) + xPlus, int(clientY) + yPlus)).start()
                    except:
                        pass 

    if "/getScreenSize" in requestPath:
        (x, y) = pyautogui.size()
        return createHttpResponse(str(x) + "," + str(y))
    
    if "/mouseWhell" in requestPath:
        if checkUser(requestPath):
            y = requestPath.split("y=")[1].split(";")[0]
            threading.Thread(target=pyautogui.scroll, args=(int(y),)).start()

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

    if "/keyboarding/" in requestPath:
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

                keyLocation = requestPath.split("location=")[1].split(";")[0]

                # print("# key down => ", key + keyLocation)

                time.sleep(0)

                if "keydown=true" in requestPath:

                    threading.Thread(target=pyautogui.keyDown, args=(key + keyLocation,)).start()
                    
                    for userInfo in userInfoList:
                        if "/?userId=" + userInfo["userId"] in requestPath:
                            break

                    if {key: "down"} not in keyStatusMap: 
                        keyStatusMap.append({"key": key, key: "down", "ns":time.perf_counter_ns(), "userId":userInfo["userId"]})
                else:
                    for keyStatus in keyStatusMap:
                        if keyStatus["key"] == key:
                            keyStatusMap.remove(keyStatus)

                    threading.Thread(target=pyautogui.keyUp, args=(key + keyLocation,)).start()

    if "/getScreenCount/" in requestPath:
        return createHttpResponse(str(len(screeninfo.get_monitors())))

    if "/screenshotRouter2/" in requestPath:
        if checkUser(requestPath) == True:
            if getScreenIndex(requestPath) != None:
                image = getScreenCapture(getScreenIndex(requestPath))
                if image != None:
                    return createHttpResponse(image, contentType="image/jpeg")

    return createHttpResponse("")

def clientIORoutine(clientSocket):
    httpRequestHeader = ""

    while True:
        try:
            recvedByte = clientSocket.recv(1)
        except BlockingIOError:
            continue

        httpRequestHeader += recvedByte.decode('utf-8')

        if "\r\n\r\n" in httpRequestHeader:
            break 

    requestPath = httpRequestHeader.split(" ")[1].split(" ")[0]

    # print("#", requestPath, " => processing..")

    httpResponse = clientIOSubRoutine(requestPath)
    clientSocket.send(httpResponse)

    # print("#", requestPath, " => done!")

    return

            
def init() -> socket.socket:
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSocket.bind(("", 9000))
    serverSocket.listen(20)

    return serverSocket 

def main():
    threading.Thread(target=userStatusManager).start()
    
    serverSocket = init()
    readySockets = [ serverSocket, ]

    while True:
        readReadySockets, writeReadySockets, exceptedSockets = select.select(readySockets, [], [])
        
        for readReadySocket in readReadySockets:
            if readReadySocket == serverSocket:
                (clientSocket, clientAddress) = serverSocket.accept()
                readySockets.append(clientSocket)
            else: 
                print(readReadySocket)

                clientIORoutine(readReadySocket)
                readReadySocket.shutdown(socket.SHUT_RDWR)
                readReadySocket.close()
                
                readySockets.remove(readReadySocket)
        
        time.sleep(0)
        
    return 

if __name__ == "__main__":
    main()