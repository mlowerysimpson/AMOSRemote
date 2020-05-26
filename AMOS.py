# Copyright (C) 2019 In Nature Robotics Ltd.
# Subject to your agreement of the disclaimer set forth below, permission is given by In Nature Robotics Ltd. to you to freely modify, redistribute or include this SNAPpy code in any program. 
# BY USING ALL OR ANY PORTION OF THIS SNAPPY CODE, YOU ACCEPT AND AGREE TO THE BELOW DISCLAIMER. If you do not accept or agree to the below disclaimer, then you may not use, modify, or distribute this SNAPpy code.
# THE CODE IS PROVIDED UNDER THIS LICENSE ON AN "AS IS" BASIS, WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, WITHOUT LIMITATION, WARRANTIES THAT THE COVERED CODE IS FREE OF DEFECTS, MERCHANTABLE, FIT FOR A PARTICULAR PURPOSE OR NON-INFRINGING. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE COVERED CODE IS WITH YOU. SHOULD ANY COVERED CODE PROVE DEFECTIVE IN ANY RESPECT, YOU (NOT THE INITIAL DEVELOPER OR ANY OTHER CONTRIBUTOR) ASSUME THE COST OF ANY NECESSARY SERVICING, REPAIR OR CORRECTION. UNDER NO CIRCUMSTANCES WILL SYNAPSE BE LIABLE TO YOU, OR ANY OTHER PERSON OR ENTITY, FOR ANY LOSS OF USE, REVENUE OR PROFIT, LOST OR DAMAGED DATA, OR OTHER COMMERCIAL OR ECONOMIC LOSS OR FOR ANY DAMAGES WHATSOEVER RELATED TO YOUR USE OR RELIANCE UPON THE SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES OR IF SUCH DAMAGES ARE FORESEEABLE. THIS DISCLAIMER OF WARRANTY AND LIABILITY CONSTITUTES AN ESSENTIAL PART OF THIS LICENSE. NO USE OF ANY COVERED CODE IS AUTHORIZED HEREUNDER EXCEPT UNDER THIS DISCLAIMER.

from synapse.switchboard import *
NUM_ATODS = 10  # the number of A to D measurements required to make sure that the output is stable
otherNodeAddr = "\x13\xB7\x90" # <= put the address of the OTHER node here

RED_LED = 23    # pin used for red LED wired to RF220SU
ACTIVITY_PIN = 20    #pin used for monitoring Raspberry Pi activity (also set to output sometimes when booting up Pi)
RELAY_OUT_PIN = 19   #pin used for controlling relay switch (turning off Raspberry Pi)
AIR_PROP_PIN = 7     #pin used for keeping air propeller in "stopped" state when Raspberry Pi is powered down
CELL_POWER_PIN = 6   #pin used for controlling power to the cell data hotspot

cycleCount = 0 #used for flashing LED and  when to enable serial port
inactivityCount = 0 #used to count how long the Raspberry Pi activity output has been idle
activityCount = 0 #used to count changes in the state of the ACTIVITY pin (indicating Raspberry Pi activity)
activitySinceLastTick = 0 #used to count changes in the state of the ACTIVITY pin (indicating Raspberry Pi activity) since the last 1 second tick time.
uart_started = 0 #set to 1 after the UART has been setup
piOff = 0 #set to 1 when Pi is turned off
piOffCount = 0 #the number of seconds that the Raspberry Pi has been turned off
activityOutputCount = 0 #used for counting how many more seconds the ACTIVITY_PIN should be kept as an output (after Raspberry Pi has been rebooted, without AMOS program running)
wakeupCommandCountdown = 0#used for adding a small delay between receipt of a "wakeup Pi" command and the actual waking up of the Pi


sleepTimeMinutes = 0 #the length of time to sleep required to power down AMOS in minutes
sleepCountSeconds = 0 #variable used to keep track of how much longer AMOS should be powered down
coutdownToSleep = 0 #the number of seconds left remaining before the Raspberry Pi will be turned off

  
def setSerPortForWireless():
    """Assign UART1 to go over wireless (no longer works in Portal after this function is called)"""
    # Initialize serial ports
    initUart(0,38400) # set UART0 to baud rate of 38400 bps
    initUart(1, 38400) # set UART1 to baud rate of 38400 bps
    flowControl(0, False) # disable flow control for UART0
    flowControl(1, False) # disable flow control for UART1
    crossConnect(DS_UART0, DS_STDIO) #connect UART0 to stdio (i.e. to this script)
    crossConnect(DS_UART1, DS_TRANSPARENT) #connect UART1 to wireless radio    
    stdinMode(0, False) #set stdin to trigger every time a CR/LF is received and disable echo on stdin
    ucastSerial(otherNodeAddr)
    
def OutputWirelessStatus():
    """Get the wireless link quality and output it to stdout (i.e. UART0)"""
    link_quality = getLq()
    if link_quality==0:
        print 'Link: N.A.'
    else:
        print 'Link: -', link_quality, ' dBm'
        
def OutputCurrentDraw():
    """Get the current draw and output it to stdout """
    global piOff
    i=0
    while i<NUM_ATODS:
        current_counts = readAdc(0) 
        i+=1
    print 'Current = ', current_counts
    
def OutputSolarVoltages():
    """Get the solar input voltages (- and +) and output them to stdout (i.e. UART0"""
    i=0
    while i<NUM_ATODS:
        solar_volt_neg = readAdc(1)
        i+=1
    i=0
    while i<NUM_ATODS:
        solar_volt_pos = readAdc(2)
        i+=1    
    print 'Solarneg = ', solar_volt_neg
    print 'Solarpos = ', solar_volt_pos
    
def setLedCount(count):
    """Display rotating-bit on LEDs"""
    global piOff
    count %= 2
    if piOff>0:
        writePin(RED_LED,0)
    else:
        writePin(RED_LED, count != 0)
    
    
def shutDownPi():
    """shutdown power to the Raspberry Pi"""
    global piOffCount
    global piOff
    global inactivityCount
    global activityCount
    global activitySinceLastTick
    writePin(RELAY_OUT_PIN, True) #put relay in on-state (removes power from Raspberry Pi)
    piOffCount=0 #reset count (in seconds that Pi has been turned off)
    piOff = 1 #flag indicates that Pi has been turned off
    inactivityCount = 0 #reset inactivity count
    activityCount = 0 #reset activity count
    activitySinceLastTick = 0 #reset activity since last tick count
    crossConnect(DS_STDIO, DS_TRANSPARENT) #switch connection between stdio and wireless, allow for wireless remote commands to wake the Pi back up
    setPinDir(AIR_PROP_PIN, True) #set AIR_PROP pin for output to air propeller to keep it still and get rid of the beeping noise while the Raspberry Pi is powered down
    
def turnOnPi(autoStartAMOS):
    """turn power back on to the Raspberry Pi, after it has been off for a while"""
    #autoStartAMOS is 0 if the AMOS program should not be started automatically after booting
    #autoStartAMOS is 1 if the AMOS program should be started automatically after booting
    global piOff
    global piOffCount
    global inactivityCount
    global activityCount
    global activitySinceLastTick
    global activityOutputCount
    global sleepTimeMinutes #length of time left in minutes for sleep
    setPinDir(ACTIVITY_PIN,True)#set activity pin to output
    if autoStartAMOS==0:
        #do not automatically start AMOS program after bootup, accomplish this by setting ACTIVITY_PIN to output high
        writePin(ACTIVITY_PIN,True)
    else:
        writePin(ACTIVITY_PIN,False) #set activity pin low, to allow AMOS program to start automatically
    activityOutputCount = 60 #counter variable used to hold ACTIVITY_PIN as output for 60 seconds    
    setPinDir(AIR_PROP_PIN, False) #set AIR_PROP pin for input now that Pi is powered back up and can control the air prop speed
    writePin(RELAY_OUT_PIN, False) #put relay in off-state (applies power to Raspberry Pi)
    writePin(CELL_POWER_PIN, True) #make sure power to cell USB stick is on
    setPinDir(CELL_POWER_PIN, False) #set pin to input to save power
    piOff = 0
    piOffCount = 0
    sleepTimeMinutes = 0;
    inactivityCount = 0 #reset inactivity count
    activityCount = 0 #reset activity count
    activitySinceLastTick = 0 #reset activity since last tick count
    #go back to the original cross connects
    crossConnect(DS_UART0, DS_STDIO) #connect UART0 to stdio (i.e. to this script)
    crossConnect(DS_UART1, DS_TRANSPARENT) #connect UART1 to wireless radio    
    

@setHook(HOOK_STARTUP)
def startupEvent():
    """Called at system startup"""
    # Initialize LED
    setPinDir(RED_LED, True) #set LED pin for output
    setPinDir(RELAY_OUT_PIN, True) #set relay output pin (for controlling Raspberry Pi power) for output
    setPinDir(ACTIVITY_PIN, False) #set ACTIVITY pin for input
    setPinDir(AIR_PROP_PIN, False) #set AIR_PROP pin for input
    setPinDir(CELL_POWER_PIN, False) #set CELL_POWER_PIN for input (will get pulled up by relay, so cell hotspot turned on)
    monitorPin(ACTIVITY_PIN, True) #set ACTIVITY pin to be monitored for changes (i.e. Raspberry Pi activity)
    setRate(2) #set for a sampling rate (of monitoring) of once every 10 ms
    writePin(RED_LED, True) #turn on LED
    writePin(RELAY_OUT_PIN, False) #startup relay in off-state (Raspberry Pi has power)


@setHook(HOOK_10MS)
def tick10():
    global piOff

    if piOff>0:
        pulsePin(AIR_PROP_PIN, -1000, True)
      

@setHook(HOOK_1S)
def tick():
    global cycleCount #counter variable increments every second
    global inactivityCount #used to determine if the Raspberry Pi has been inactive for a long period of time
    global activityCount
    global activitySinceLastTick
    global uart_started
    global piOff
    global piOffCount
    global sleepTimeMinutes #length of time left in minutes for sleep
    global sleepCountSeconds
    global countdownToSleep
    global activityOutputCount
    global wakeupCommandCountdown
    
    cycleCount = (cycleCount+1)%32000 #increment and avoid wraparound to negative numbers
    inactivityCount = (inactivityCount+1)%32000 #increment and avoid wraparound to negative numbers
    activitySinceLastTick = 0
    if uart_started>0:
        setLedCount(cycleCount)
    if cycleCount==60 and uart_started==0:
        setSerPortForWireless()
        uart_started=1
    if piOff==0 and inactivityCount>=120 and activityCount >=10:
        #Raspberry Pi was active for at least 10 seconds, but has been inactive for the last 2 minutes, need to reboot it to get it going again
        inactivityCount=0
        activityCount=0
        shutDownPi()#shutdown power to the Raspberry Pi
    if countdownToSleep>0:
        countdownToSleep -= 1 #decrement countdown to sleep value (for doing a planned shutdown of the Raspberry Pi)
        if countdownToSleep==0:
            shutDownPi()#shutdown power to the Raspberry Pi
            setPinDir(CELL_POWER_PIN,True)#set cellular power pin to output
            writePin(CELL_POWER_PIN,False)#set cellular power pin low, to turn off power to the cellular hotspot
    if piOff>0:
        if sleepTimeMinutes==0:
            #Raspberry Pi was turned off due to inactivity
            piOffCount += 1
            if piOffCount == 10:
                piOff=0
                piOffCount=0
                turnOnPi(1)#turn power back on to the Raspberry Pi, after it has been off for 10 seconds, and automatically start AMOS program
        else:
            #Raspberry Pi was turned off for a planned shutdown
            sleepCountSeconds += 1
            if sleepCountSeconds==60:
                #another minute of sleep has elapsed
                sleepTimeMinutes -= 1#decrement remaining sleep time in minutes 
                sleepCountSeconds = 0#reset sleep seconds counter to zero
                if sleepTimeMinutes==0:
                    #time to wake up Raspberry Pi (from its planned shutdown)
                    piOff=0
                    piOffCount=0
                    turnOnPi(1)
                elif sleepTimeMinutes<=2:
                    #turn on power to cellular hotspot (2 minutes in advance of time when Raspberry Pi will be turned on)
                    writePin(CELL_POWER_PIN, True)#set pin output to high to turn on power to cell hotspot
                    setPinDir(CELL_POWER_PIN,False)#set pin back to input       
                   
    if activityOutputCount>0:
        activityOutputCount -= 1
        if activityOutputCount==0:
            writePin(ACTIVITY_PIN, False) #set ACTIVITY pin to low
            #set ACTIVITY_PIN back to input
            setPinDir(ACTIVITY_PIN, False) #set ACTIVITY pin for input
    if wakeupCommandCountdown>0:
        wakeupCommandCountdown -= 1
        if wakeupCommandCountdown == 0:
            turnOnPi(0)
                

@setHook(HOOK_STDIN)
def stdinEvent(buf):
    """Receive handler for character input on UART0.
       The parameter 'buf' will contain one or more received characters. 
    """
    global sleepTimeMinutes
    global sleepCountSeconds
    global countdownToSleep
    global piOff
    global wakeupCommandCountdown
    
    n = len(buf)
        
    if n>=5 and buf[0]=='d' and buf[1]=='o' and buf[2]=='w' and buf[3]=='n': #put pi to sleep for specified time
        sleepTimeMinutes = int(buf[4:])
        sleepCountSeconds = 0        
        countdownToSleep = 15 #15 second countdown used to give Pi enough time to halt its various processes 
    elif n>=5 and buf[0]=='s' and buf[1]=='l' and buf[2]=='e' and buf[3]=='e' and buf[4]=='p': #sleep command, put pi to sleep indefinitely (until manually woken)
        shutDownPi() #turn off Raspberry Pi
    elif n>=7 and buf[0]=='c' and buf[1]=='u' and buf[2]=='r' and buf[3]=='r' and buf[4]=='e' and buf[5]=='n' and buf[6]=='t':  #request for current measurement  
        OutputCurrentDraw()
    elif n>=5 and buf[0]=='s' and buf[1]=='o' and buf[2]=='l' and buf[3]=='a' and buf[4]=='r': #request for solar voltages
        OutputSolarVoltages()
    elif n>=5 and buf[0]=='p' and buf[1]=='o' and buf[2]=='w' and buf[3]=='e' and buf[4]=='r': #request for wireless received power level in dBm
        OutputWirelessStatus()
    elif n>=6 and buf[0]=='w' and buf[1]=='a' and buf[2]=='k' and buf[3]=='e' and buf[4]=='u' and buf[5]=='p': #wakeup AMOS from sleep
        if piOff>0:
            print 'wakeup received' #acknowledge that command to wakeup Raspberry Pi was received
            wakeupCommandCountdown = 5 #set countdown before waking up Pi, makes sure that acknowledgement text gets properly sent
        

@setHook(HOOK_GPIN)
def pinChg(pinNum, isSet):
    """Called whenever a GPIO pin changes"""
    global inactivityCount
    global activityCount
    global activitySinceLastTick
    
    if pinNum==ACTIVITY_PIN:
        #some Raspberry Pi activity has been detected
        inactivityCount = 0
        activityCount += 1     
        activitySinceLastTick += 1    
        if activitySinceLastTick>=3:
            activityCount = 0 #burst of activity was detected, so reset activity count to zero, this indicates that the Raspberry Pi program was shut down normally
