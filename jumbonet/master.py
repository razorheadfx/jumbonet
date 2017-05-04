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
        
    def add_remote(self, name, host, user, keyfile = None, port = 22):
        try:
            r = remote.Remote(name, host, user, keyfile = keyfile, port =  port)
        except:
            raise
        
        self.remotes[name] = r
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
        
        log.info("Shutting down remotes:")
        for remote in self.remotes.values():
            print("-- shutting down %s" %remote.name)
            remote.shutdown()
        
  
    def __watch_remotes(self):
        log.debug("Watching remotes")
        for r in self.remotes.values():
            r.check_processes()
            
class Listener():
    
    def __init__(self):
        pass
    
    def receive_out(self,remotename, uuid, lines):
        for line in lines:
            print("%s:%s" %(uuid, line))
        raise NotImplementedError()
    
    def receive_err(self,remotename, uuid, lines):
        for line in lines:
            print("%s:%s" %(uuid, line))
        raise NotImplementedError()
    
    def receive_status(self,remotename, uuid, alive):
        raise NotImplementedError()
