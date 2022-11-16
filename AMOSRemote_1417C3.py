# Copyright (C) 2019 In Nature Robotics Ltd.
# Subject to your agreement of the disclaimer set forth below, permission is given by Simpson's Helpful Software to you to freely modify, redistribute or include this SNAPpy code in any program. 
# BY USING ALL OR ANY PORTION OF THIS SNAPPY CODE, YOU ACCEPT AND AGREE TO THE BELOW DISCLAIMER. If you do not accept or agree to the below disclaimer, then you may not use, modify, or distribute this SNAPpy code.
# THE CODE IS PROVIDED UNDER THIS LICENSE ON AN "AS IS" BASIS, WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, WITHOUT LIMITATION, WARRANTIES THAT THE COVERED CODE IS FREE OF DEFECTS, MERCHANTABLE, FIT FOR A PARTICULAR PURPOSE OR NON-INFRINGING. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE COVERED CODE IS WITH YOU. SHOULD ANY COVERED CODE PROVE DEFECTIVE IN ANY RESPECT, YOU (NOT THE INITIAL DEVELOPER OR ANY OTHER CONTRIBUTOR) ASSUME THE COST OF ANY NECESSARY SERVICING, REPAIR OR CORRECTION. UNDER NO CIRCUMSTANCES WILL SYNAPSE BE LIABLE TO YOU, OR ANY OTHER PERSON OR ENTITY, FOR ANY LOSS OF USE, REVENUE OR PROFIT, LOST OR DAMAGED DATA, OR OTHER COMMERCIAL OR ECONOMIC LOSS OR FOR ANY DAMAGES WHATSOEVER RELATED TO YOUR USE OR RELIANCE UPON THE SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGES OR IF SUCH DAMAGES ARE FORESEEABLE. THIS DISCLAIMER OF WARRANTY AND LIABILITY CONSTITUTES AN ESSENTIAL PART OF THIS LICENSE. NO USE OF ANY COVERED CODE IS AUTHORIZED HEREUNDER EXCEPT UNDER THIS DISCLAIMER.

#Script for Base Node
from synapse.switchboard import *

otherNodeAddr = "\x14\x17\x5B" # <= put the address of the OTHER (remote) node here
GREEN_LED = 7    # pin used for green LED wired to RF220SU
BLUETOOTH_ENABLE = 23    # pin used for enabling the HM10 Bluetooth Module
WARMUP_TIME_SEC = 60     # warmup time in seconds before launching wireless communications (IMPORTANT: once communications are launched, a direct connection with the Portal software is not possible.)
cycleCount = 0
uart_started = 0

@setHook(HOOK_STARTUP)
def startupEvent():
    """Called at system startup"""
    # Initialize LED
    setPinDir(GREEN_LED, True) #set LED pin for output
    setPinDir(BLUETOOTH_ENABLE, True) #set BLUETOOTH_ENABLE pin for output
    writePin(GREEN_LED, True) #turn on LED
    writePin(BLUETOOTH_ENABLE, False) #disable HM10 Bluetooth Module communications
    
def setLedCount(count):
    """Display rotating-bit on LEDs"""
    count %= 2
    writePin(GREEN_LED, count != 0)
    
def setSerPortForWireless():
    """Assign UART1 to go over wireless (no longer works in Portal after this function is called)"""
    # Initialize serial ports
    #initUart(0,1) # set UART0 to baud rate of 115200 bps
    initUart(1, 38400) # set UART1 to baud rate of 38400 bps
    #flowControl(0, False) # disable flow control for UART0
    flowControl(1, False) # disable flow control for UART1
    crossConnect(DS_UART1, DS_TRANSPARENT) #connect UART1 to wireless radio
    #crossConnect(DS_UART0, DS_STDIO) #connect UART0 to stdio (i.e. to this script)
    #stdinMode(0, False) #set stdin to trigger every time a CR/LF is received and disable echo on stdin
    ucastSerial(otherNodeAddr)
    
def OutputWirelessStatus():
    """Get the wireless link quality and output it to stdout (i.e. UART0)"""
    link_quality = getLq()
    if link_quality==0:
        print 'Link: N.A.'
    else:
        print 'Link: -', link_quality, ' dBm'

@setHook(HOOK_1S)
def tick():
    global cycleCount
    global uart_started
    cycleCount += 1
    if uart_started>0:
        setLedCount(cycleCount)
    if cycleCount==WARMUP_TIME_SEC and uart_started==0:
        setSerPortForWireless()
        uart_started=1


        
    