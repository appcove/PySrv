# vim:tabstop=4:shiftwidth=4:expandtab:autoindent:softtabstop=4
# NOTE: 4 spaces used for indent!!!

"""
Copyright (c) 2011, AppCove, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or 
without modification, are permitted provided that the 
following conditions are met:

* Redistributions of source code must retain the above 
  copyright notice, this list of conditions and the 
  following disclaimer.

* Redistributions in binary form must reproduce the above 
  copyright notice, this list of conditions and the 
  following disclaimer in the documentation and/or other 
  materials provided with the distribution.

* Neither the name of the IonZoft, Inc. nor the names of 
  its contributors may be used to endorse or promote 
  products derived from this software without specific 
  prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND 
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, 
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF 
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR 
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, 
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF 
SUCH DAMAGE.

-----------------------------------------------------------
Refactored to work with Python 2.4.4


-----------------------------------------------------------
Server Control:
    Init()
        Initialize the server
    
    Run()
        Run the server
        
    Stop()
        Stop the server


-----------------------------------------------------------
Waiting for Connections:
    ListenerThread class
        Handles details of waiting for connections
    
    Listener 
        global variable that points to a single ListenerThread
        instance.


-----------------------------------------------------------
Networking details
    BlockingPacketConnection
        Handles the details of sending and receiving packets
        that are delimited by a fixed delimiter

    ClientConnection
        A subclass of BlockingPacketConnection which handles
        the details of communicating with a remote client.

-----------------------------------------------------------
The actual work...
    ClientTread
        A class which represents each client connection
        and the activity that needs to go on in order to 
        support that client.


"""

import sys
import time
import re

import socket
import os
from os import path
import threading
import signal

try:
    import fcntl
except ImportError:
    fcntl = None

import __builtin__

import traceback

###################################################################################################
# Debugging support

__builtin__.DE = 0

def BUG(level, msg):
    if DE >= level:
        sys.stdout.write("[Debug%s] %s\n\n" % (level, msg))

def EnableDEBUG(level):
    __builtin__.DE = level
    __builtin__.BUG = BUG


# Example of debugging support:
# if DE:BUG(3, "This is a level three message")


###############################################################################
# Global Variables

# Is the server running?
Running = False
Running_Lock = threading.Lock()

# A reference to the ListenerThread object
Listener = None

###############################################################################
# Signal Handling

def SIGINT(a,b):
    if Running:
        Stop()
    else:
        print "Goodbye."
        sys.exit()

def SIGTERM(a,b):
    print "Caught SIGTERM. Stopping..."
    Stop()
    sys.exit()

# A handler for the interrupt
signal.signal(signal.SIGINT, SIGINT)

# We DO NOT want to have to reap children
if hasattr(signal, 'SIGCHLD'):
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)

# Gracefully handle SIGTERM
signal.signal(signal.SIGTERM, SIGTERM)



###############################################################################
# Server Initialization 

def Init(AS_Address, AS_Port):
    """
    Server Initialization.  Must be called before Run().
    Pass the AF_INET address and port: eg "localhost", 8888
    """

    if DE:BUG(1, "Initializing Server...")
    
    global Listener
    
    Listener = ListenerThread(AS_Address, AS_Port)
    Listener.start()



###############################################################################

def Run():
    """
    This is the main server loop.  Although most of the functionality is 
    threaded, this could be used for periodic checking of things, etc...
    """
    
    global Running
    
    # Acquire running lock and set Running to True
    try:
        Running_Lock.acquire()
        Running = True
    finally: 
        Running_Lock.release()
    
    if DE:BUG(1, "Started Server.")
    
    # Loop while running
    while Running:
        time.sleep(1.00)

        #TODO: Could put status checks, etc here

    if DE:BUG(1, "Stopped Server.")



###############################################################################

def Stop():
    """
    Stops the server.  Can be called from anywhere.
    """
    
    if DE:BUG(1, "Stopping Server...")
    global Running
    
    try:
        Running_Lock.acquire()
        Running = False
    finally: 
        Running_Lock.release()




###############################################################################
class ListenerThread(threading.Thread):
    """
    This class represents a Listener for incoming connections.  
    
    It establishes a listener socket, and begins listening.

    Upon establishment of a new connection, a ClientThread is spawned, and 
    this thread resumes listening for another connection.
   
    """


    #==========================================================================
    def __init__(self, AS_Address, AS_Port):
        
        threading.Thread.__init__(self)
    
        # this thread should NOT keep the server alive
        self.setDaemon(True)

        # Set defaults
        self.Backlog = 1
        self.Address = (AS_Address, AS_Port)

        # Create the listener socket (AF_INET)
        self._Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Tell the socket to reuse the address if needed.  Otherwise, one
        # would have to wait roughly 2 minutes before rebinding to the address
        self._Socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind this socket to the address.
        self._Socket.bind(self.Address)
        
        # We do not want this file descriptor to live past a call to exec()
        if fcntl:
            fcntl.fcntl(self._Socket.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)

        # Begin listening!
        self._Socket.listen(self.Backlog)
    
        if DE:BUG(2, "Listener listening on %s" % str(self.Address))
    
    #==========================================================================
    def run(self):
            
        if DE:BUG(2, "Listener waiting for connections on %s" % str(self.Address))
    
        # Loop and accept connections.  Repeat.
        while True:
        
            # Accept the connection
            conn, addr = self._Socket.accept()

            if DE:BUG(3, "Client accepted: %s, %s" % (conn, str(addr)))

            # Spawn the client thread, and start it.
            ClientThread(conn, addr).start()

            # Remove these references, otherwise the connection may stay
            # open until they are overrun by another connection.
            del(conn, addr)
    

    
###############################################################################
class ClientThread(threading.Thread):
    """
    The objective of a ClientThread is to handle all communication with 
    a client, and any upstream service providers.

    This object implements a stack of objects that are derived from the class
    BlockingPacketConnection.

    It is designed to listen to the top of the stack.

    """

    #==========================================================================
    def __init__(self, conn, addr):
        """
        Take incoming socket and address.
        Manage all aspects of that client, including death-detection, etc...

        The ClientConnection will be Stack[0]
        """
        threading.Thread.__init__(self)
        
        
        self.Stack = [ClientConnection(conn, addr)]
            

    #==========================================================================
    def run(self):
        pass

        # Loop while there is a stack
        while len(self.Stack):
            
            #------------------------------------------------------------------
            try:
                # Receive a packet from the tip of the stack.
                # Exceptions received during reading of a packet result in an 
                # unconditional closure of that connection
                CloseConnection = True
                sPacketI = self.Stack[-1].RecvPacket()
                
                self.HandlePacket(self.Stack[-1], sPacketI)
        
            
            #------------------------------------------------------------------
            except ConnectionLost, e:
                
                dead = self.Stack.pop()
                
                if DE:BUG(3, "Connection %s lost due to: %s" % (dead, e))

                # Just get out of here, close the thread
                break 
            
            #------------------------------------------------------------------
            except Exception, e:
                
                # Print exception
                print; traceback.print_exc(); print
                
                # Format message:
                if DE:BUG(3, "Tip-of-stack %s received %s: \n%s" % (self.Stack[-1], type(e).__name__, e))
            
                # Close the connection if instructed to do in the Try block aboce
                if CloseConnection:
                    # Discard the tip of the stack
                    if DE:BUG(3, "Connection %s closed (due to above)" % self.Stack[-1])
                    self.Stack.pop().Close()

                # Just get out of here, close the thread
                break 
                
            #endtry
        
        #endwhile


    #==========================================================================
    def HandlePacket(self, oConn, sPacketI):
        """
        Called anytime an incoming packet needs handled.
        """
        

        # Packets look like "COMM: data..."
        sType = sPacketI[0:4]
        sData = sPacketI[6:]

        if sType == 'HELO':
            self.HELO(oConn, sData)
        elif sType == 'TEST':
            self.TEST(oConn, sData)
        elif sType == 'DROP':
            self.DROP(oConn, sData)
        else:   
            #raise ValueError("Unknown command: %s" % sType)
            oConn.SendPacket('I do not know that command.  Use "DROP" to exit.')
                    
    #==========================================================================
    def HELO(self, oConn, sData):
        
        #TODO: Parse sData
        #TODO: run necessary actions
        #TODO: reply

        oConn.SendPacket("CGST: AgentOnline")

    #==========================================================================
    def TEST(self, oConn, sData):
        
        #TODO: Parse sData
        #TODO: run necessary actions
        #TODO: reply

        oConn.SendPacket("TEST: you said '%s'." % sData)

    #==========================================================================
    def DROP(self, oConn, sData):
        
        #TODO: Parse sData
        #TODO: run necessary actions
        #TODO: reply

        oConn.SendPacket("EXIT: bye!")
        oConn.Close()




    
################################################################################
class ConnectionLost(Exception):
    """
    Exceptions of this type are raised by a connection object when the
    connection is dropped.
    """
    pass


################################################################################
class BlockingPacketConnection(object):

    # Class variables
    PacketDelimiter = "\r\n"  #for telnet
    BufSize = 4096
    
    # Instance variables
    Address = None
    
    _Socket = None
    _RecvBuffer = ''
    
    _LastID = 0
    _LastID_Lock = threading.Lock()
    
    # Instance attributes
    ID = None
    
    #==========================================================================
    @staticmethod 
    def NextID():
        """
        Returns the next available ID in an atomic fashion.
        This CANNOT be an instancemethod or classmethod, or else the ID's 
        will not be globally unique.
        """
        try:
            BlockingPacketConnection._LastID_Lock.acquire()
            BlockingPacketConnection._LastID += 1
            return BlockingPacketConnection._LastID
        finally:
            BlockingPacketConnection._LastID_Lock.release()
            

    #==========================================================================
    def __init__(self, sock, addr):
        
        # Address of the connection
        self.Address = addr
        
        # The actual socket
        self._Socket = sock
        
    
    #==============================================================================================
    def SendPacket(self, data):
        """
        Sends the data until it is all sent.
        """
        if DE:BUG(5, "Sending packet on on %s:\n%s" % (self, data))
        
        if data.find(self.PacketDelimiter) != -1:
            raise ValueError("The packet being queued must not contain the PacketDelimiter.")

        data += self.PacketDelimiter

        while len(data):
            bytes = self._Socket.send(data)
            data = data[bytes:]

        return

    #==========================================================================
    def RecvPacket(self):
        """
        This function will read on the socket until it receives enough data
        to form a packet, or else die trying.

        It either returns a packet, or a ConnectionLost exception, or possible
        a socket-oriented exception.
        """
        
        while True:
            
            pos = self._RecvBuffer.find(self.PacketDelimiter)

            if pos >= 0:
                packet = self._RecvBuffer[0:pos]
                self._RecvBuffer = self._RecvBuffer[pos+len(self.PacketDelimiter):]
        
                if DE:BUG(5, "Packet received on %s:\n%s" % (self, packet))
                return packet

            data = self._Socket.recv(self.BufSize)

            if data == '':
                self._Socket.close()
                raise ConnectionLost("Socket closed due to zero length read.")

            self._RecvBuffer += data

    
    #==========================================================================
    def Close(self, sReason='No Reason Given'):
        """
        Close the socket
        """
        
        self._Socket.close()





###############################################################################
class ClientConnection(BlockingPacketConnection):
    """
    This handles details of a client connection.

    """
    
    # how long to wait for socket activity?
    SOCKET_TIMEOUT = 60

    
    #==========================================================================
    def __init__(self, conn, addr):
        
        # Get the ID
        self.ID = self.NextID()
        
        # Set the timeout
        conn.settimeout(self.SOCKET_TIMEOUT)
        
        # Tell it to close on exec
        if fcntl:
            fcntl.fcntl(conn.fileno(), fcntl.F_SETFD, fcntl.FD_CLOEXEC)
        
        # Call baseclass constructor
        BlockingPacketConnection.__init__(self, conn, addr)

    #==========================================================================
    def __repr__(self):
        return "<ClientConnection #%i>" % self.ID
    






