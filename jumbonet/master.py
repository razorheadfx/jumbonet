import logging
from multiprocessing.pool import ThreadPool
import time
import sys
import traceback
from . import remote

log = logging.getLogger(__name__)


class Chief():
    def __init__(self):
        self.remotes = {}
        self.run = False
        
    def add_remote(self, name, host, user, keyfile = None, port = 22, inband_ip = None, inband_mac = None, inband_interface = None):
        try:
            r = remote.Remote(name, host, user, keyfile = keyfile, port = port, inband_ip = inband_ip, inband_mac = inband_mac, inband_interface=inband_interface)
        except:
            raise
        
        self.remotes[name] = r
        log.info("Connected to Remote: %s at %s:%s" %(r.name, r.host, r.port))
        return r
        
        
    def mainloop(self):        
        log.debug("Forking mainloop")
        self.run = True
        
        pool = ThreadPool(processes = 1)
        pool.apply_async(self.__mainloop)
    
    def __mainloop(self):
        log.debug("Mainloop started")
        while self.run:
            try:
                time.sleep(0.5)
                self.__watch_remotes()
        
            except:
                traceback.print_exc()

        
    
    def shutdown(self):
        self.run = False
        
        log.info("Disconnecting remotes")
        for remote in self.remotes.values():
            remote.shutdown()
            log.info("-- Disconnected %s (%s:%s)" %(remote.name, remote.host, remote.port))
        
  
    def __watch_remotes(self):
        log.debug("Watching remotes")
        for r in self.remotes.values():
            r.check_processes()

    def kill_all_processes(self):
        for uuid, r in self.remotes.items():
            r.killall()
            r.check_processes()


    def has_running_processes(self):
        for uuid, r in self.remotes.items():
            if r.has_running_processes():
                return True

        return False
            
class Listener():
    
    def __init__(self):
        pass
    
    def receive_out(self, remotename, uuid, args, lines):
        for line in lines:
            print("%s:%s" %(uuid, line))
        raise NotImplementedError()
    
    def receive_err(self, remotename, uuid, args, lines):
        for line in lines:
            print("%s:%s" %(uuid, line))
        raise NotImplementedError()
    
    def receive_status(self, remotename, uuid, args, exitcode):
        raise NotImplementedError()
