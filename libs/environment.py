# -*- coding: utf-8 -*-
#
# state
# 08-2019, Tomas Vitvar, tomas@vitvar.com

import threading
import time

from command import Command
from threading import Timer

# VERSION
VERSION="JA-121T-emulator, SN:00000000, SWV:0000000, HWV:0"

# health interval in seconds
HEALTH_INTERVAL = 12

# constants
STATE_STATUS_OFF = "OFF"
STATE_STATUS_ARMED = "ARMED"
STATE_STATUS_READY = "READY"

# exist status for states
STATE_EXIT_ON  = "ON"
STATE_EXIT_OFF = "OFF"

# messages send back 
MSG_OK = "OK"
MSG_ERROR_GENERIC = "ERROR"
MSG_ERROR_AUTH = "ERROR: 3 NO_ACCESS"
MSG_INVALID_VALUE = "ERROR: 4 INVALID_VALUE"
MSG_ERROR_NOTIMPLEMENTED = "ERROR: NOT IMPLEMENETED"

# commands and patterns
CMD_PATTERN_VER      = "VER"
CMD_PATTERN_HELP     = "HELP"
CMD_PATTERN_STATE    = "STATE"
CMD_PATTERN_SET      = "([0-9]{4}) SET ([0-9\ ]+)"
CMD_PATTERN_UNSET    = "([0-9]{4}) UNSET ([0-9\ ]+)"
CMD_PATTERN_SETP     = "([0-9]{4}) SETP ([0-9\ ]+)"
CMD_PATTERN_PGON     = "([0-9]{4}) PGON ([0-9\ ]+)"
CMD_PATTERN_PGOFF    = "([0-9]{4}) PGOFF ([0-9\ ]+)"
CMD_PATTERN_PGSTATE  = "PGSTATE"
CMD_PATTERN_FLAGS    = "STATE"
CMD_PATTERN_PRFSTATE = "PRFSTATE"

# authentication codes
CODES = ["4321", "1234"]

# envirionment with intial data
class Environment:
    def __init__(self, notify, stop_event):
        self.notify = notify;
        self.stop_event = stop_event
        
        self.states=States([State(x+1, notify=self.notify) for x in range(15)])
        self.states.states[0].status = STATE_STATUS_READY
        self.states.states[0].exit_delay = 5
        self.states.states[1].status = STATE_STATUS_ARMED
        self.states.states[2].status = STATE_STATUS_ARMED
        
        self.health = threading.Thread(target = self.report_health)
        self.health.start()
        
        self.pgstates=None
        self.prfstates=None
                
        # commands
        self.commands = [
            Command(CMD_PATTERN_VER, "VER: Show version information", lambda : "%s\n%s\n"%(VERSION,MSG_OK)), 
            Command(CMD_PATTERN_HELP, "HELP: Show this help text", self.command_help), 
            Command(CMD_PATTERN_SET, "SET: Turn sections to SET state (space separated section numbers)", self.states.command_set), 
            Command(CMD_PATTERN_SETP, "SETP: Turn sections to partially SET state", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED),
            Command(CMD_PATTERN_UNSET, "UNSET: Turn sections to UNSET state", self.states.command_unset),
            Command(CMD_PATTERN_PGON, "PGON: Turn ON PG (space separated pg numbers)", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED),
            Command(CMD_PATTERN_PGOFF, "PGOFF: Turn OFF PG", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED),
            Command(CMD_PATTERN_STATE, "STATE: Get system state (optionaly space separated section numbers)", self.states.command_state),
            Command(CMD_PATTERN_PGSTATE, "PGSTATE: Get PG state (optionaly space separated pg numbers)", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED),
            Command(CMD_PATTERN_FLAGS, "FLAGS: Get system alarm flags", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED),
            Command(CMD_PATTERN_PRFSTATE, "PRFSTATE: Get periphery state (bitmap hex-dump)", lambda : "%s\n"%MSG_ERROR_NOTIMPLEMENTED)
        ]

    def report_health(self):
        while not self.stop_event.wait(HEALTH_INTERVAL):
            if not self.stop_event.is_set():
                self.notify(str("%s\n"%MSG_OK).encode())
    # // report_health

    def match_and_execute(self, cmdstr):
        for command in self.commands:
            res=command.match_and_execute(cmdstr)
            if res is not None:
                return res
        return "ERROR\n"
    # // match_and_execute
        
    def command_help(self):
        return "usage\n    " \
          "[pass] command1 [params][; command2 ... ]\n" \
          "commands:\n" + ("\n".join([ "    " + cmd.help for cmd in self.commands ])) + "\n\n%s\n"%MSG_OK
    # // command_help
    
# list of states
class States:
    def __init__(self, states=[]):
        self.states = states 
    # // init

    def add(self, state):
        self.states.append(state)
    # // init

    def valid_sections(self,nums,valid_statuses):
        try:
            nl = [ int(n.strip()) for n in nums.split(' ') ]
            return [ s.num for s in self.states if s.status in valid_statuses and s.num in nl ]
        except:
            return []
    # // valid_sections    
    
    def command_state(self):
        return "STATE:\n" + "".join([ state.status_msg() for state in self.states ]) + "%s\n"%MSG_OK
    # // command_states

    def command_set(self, code, nums):
        if not code in CODES:
            return "%s\n"%MSG_ERROR_AUTH
        
        # get valid sections
        nl = self.valid_sections(nums, [STATE_STATUS_READY]) 
        if len(nl)==0:
            return "%s\n"%MSG_INVALID_VALUE
        
        for state in self.states:
            if state.num in nl:
                err = state.set()
                if err is not None:
                    return err
                    
        return "%s\n"%MSG_OK
    # // command_set    

    def command_unset(self, code, nums):
        if not code in CODES:
            return "%s\n"%MSG_ERROR_AUTH
        
        # get valid sections
        nl = self.valid_sections(nums, [STATE_STATUS_ARMED]) 
        if len(nl)==0:
            return "%s\n"%MSG_INVALID_VALUE

        for state in self.states:
            if state.num in nl:
                err = state.unset()
                if err is not None:
                    return err
                    
        return "%s\n"%MSG_OK
    # // command_unset    

# single state
class State:
    def __init__(self, num, status=STATE_STATUS_OFF, exit_delay=0, name=None, notify=None):
        # core properties
        self.num = num
        self.status = status
        self.exit_delay = exit_delay
        self.exit_status = STATE_EXIT_OFF
        self.notify = notify
    
        # additional properties
        self.name = name
                
    def exit_set(self):
        if self.exit_delay > 0 and self.exit_status == STATE_EXIT_OFF:
            self.exit_status = STATE_EXIT_ON
            self.notify(str(self.exit_msg()).encode())
            Timer(self.exit_delay, self.exit_unset).start()

    def exit_unset(self):
        if self.exit_delay > 0 and self.exit_status == STATE_EXIT_ON:
            self.exit_status = STATE_EXIT_OFF
            self.notify(str(self.exit_msg()).encode())                    
                
    def set(self):
        if self.status == STATE_STATUS_READY:
            self.status = STATE_STATUS_ARMED
            self.exit_set()                            
            self.notify(str(self.status_msg()).encode())
        else:
            return "%s\n"%MSG_ERROR_GENERIC
        return None
    # // set
    
    def unset(self):
        if self.status == STATE_STATUS_ARMED:
            self.status = STATE_STATUS_READY
            self.exit_unset()                            
            self.notify(str(self.status_msg()).encode())
        else:
            return "%s\n"%MSG_ERROR_GENERIC
        return None
    # // unset        
    
    def status_msg(self):
        return "STATE %s %s\n"%(self.num, self.status)     

    def exit_msg(self):
        return "EXIT %s %s\n"%(self.num, self.exit_status)             
        