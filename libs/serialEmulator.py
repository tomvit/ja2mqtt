# serial emulator, based on a code from D. Thiebaut for fake serial for Arduino

import time
import threading

from environment import Environment

def serial_for_url(port, do_not_open=True):
    ser=Serial(port)
    if not do_not_open:
        ser.open()
    return ser

# a Serial class emulator 
class Serial:

    ## init(): the constructor.  Many of the arguments have default values
    # and can be skipped when calling the constructor.
    def __init__( self, port='COM1', baudrate = 19200, timeout=1,
                  bytesize = 8, parity = 'N', stopbits = 1, xonxoff=0,
                  rtscts = 0):
        self.name     = port
        self.port     = port
        self.timeout  = timeout
        self.parity   = parity
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.xonxoff  = xonxoff
        self.rtscts   = rtscts
        self.is_open  = False
        self.in_waiting = 0
        self._data = ""
        
        self.stop_event = None
        self.env=None
        
    ## isOpen()
    # returns True if the port to the Arduino is open.  False otherwise
    def isOpen(self):
        return self.is_open

    ## open()
    # opens the port
    def open(self):
        if not self.is_open:
            self.stop_event = threading.Event()
            self.env=Environment(self.notify, self.stop_event)        
            self.is_open = True

    ## close()
    # closes the port
    def close( self ):
        print('closing...')
        if self.is_open:
            self.stop_event.set()
            self.stop_event=None
            self.env = None
            self.is_open = False

    def notify(self, data):
        self._data += data.decode('utf-8');
        self.in_waiting = len(self._data)

    ## write()
    # writes a string of characters to the internal buffer
    def write( self, data ):
        rcv = data.decode('utf-8')
        if rcv[-1] == '\n':
            # execute the command and get back the output
            d = self.env.match_and_execute(rcv) + "\n"
            self._data += d
            self.in_waiting = len(self._data)

    ## read()
    # blocking read; when n > 0, then will be waiting for data
    def read( self, n=1 ):
        out = ''
        if n > 0:
            while len(self._data) < n:
                time.sleep(0.01)
                
            out = self._data[0:n]
            self._data = self._data[n:]      
            self.in_waiting = len(self._data)      
            
        return str.encode(out)

    ## readline()
    def readline( self ):
        returnIndex = self._data.index( "\n" )
        if returnIndex != -1:
            s = self._data[0:returnIndex+1]
            self._data = self._data[returnIndex+1:]
            self.in_waiting = len(self._data)
            return str.encode(s)
        else:
            return str.encode("")

    ## __str__()
    def __str__( self ):
        return  "Serial<id=0xa81c10, open=%s>( port='%s', baudrate=%d," \
               % ( str(self.is_open), self.port, self.baudrate ) \
               + " bytesize=%d, parity='%s', stopbits=%d, xonxoff=%d, rtscts=%d)"\
               % ( self.bytesize, self.parity, self.stopbits, self.xonxoff,
                   self.rtscts )
