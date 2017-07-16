import logging
from multiprocessing.pool import ThreadPool
import time
import sys
import traceback
from . import remote

log = logging.getLogger(__name__)


class Master():
    def __init__(self, default_keyfile = None, default_user = None, default_inband_interface = "eth0"):
        self.remotes = {}
        self.run = False

        #used for convenience in mininet-like function addHost
        self.default_keyfile = default_keyfile
        self.default_user = default_user
        self.default_inband_interface = default_inband_interface
        
    def add_remote(self, name, host, user, remote_password = None, keyfile = None, port = 22,  \
                   inband_ip = None, inband_mac = None, inband_interface = None):

        if keyfile is None and remote is None:
            raise Exception("Either provide remote_password in plaintext (not recommended) or keyfile=path/to/ssh/private/key")

        try:
            r = remote.Remote(name, host, user, keyfile = keyfile, remote_password=remote_password, port = port, \
                              inband_ip = inband_ip, inband_mac = inband_mac, inband_interface=inband_interface)
        except:
            raise
        
        self.remotes[name] = r
        log.info("Connected to Remote: %s at %s:%s" %(r.name, r.host, r.port))
        return r

    def addHost(self, name, ip, mac, **kwargs):
        """the mininet-friendly variant, requires default_keyfile, default_user to be set"""

        keyfile = kwargs.get("keyfile", self.default_keyfile)
        remote_host = kwargs.get("remote_host")
        remote_user = kwargs.get("remote_user", self.default_user)
        inband_iface = kwargs.get("inband_iface", self.default_inband_interface)

        if remote_host is None:
            raise Exception("No remote_host provided")

        return self.add_remote(name, remote_host, remote_user, keyfile = keyfile, port = 22, \
                               inband_ip=ip, inband_mac=mac, inband_iface=inband_iface)

        
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

        
    def stop(self):
        """the mininet-friendly variant"""
        self.shutdown()

    def shutdown(self):
        self.run = False
        
        log.info("Disconnecting remotes")
        for remote in self.remotes.values():
            remote.shutdown()
            log.info("-- Disconnected {} ({}:{})".format(remote.name, remote.host, remote.port))
        
  
    def __watch_remotes(self):
        log.debug("Watching remotes")
        for r in self.remotes.values():
            r.check_processes()

    def kill_process(self, uuid, remotename = None):
        p = self.get_process(uuid, remotename)

        if p is not None:
            p.kill()
        else:
            log.error("Could not find {}@{}".format(uuid, remotename))


    def kill_all_processes(self):
        for uuid, r in self.remotes.items():
            r.killall()
            r.check_processes()

    def get_process(self, uuid, remotename = None):
        p = None
        if remotename is not None:
            r = self.remotes[remotename]
            p = r.get_process(uuid)

        else:
            for remote in self.remotes.values():
                p = remote.get_process(uuid)
                if p is not None:
                    return p

        return None


    def has_running_processes(self):
        for uuid, r in self.remotes.items():
            if r.has_running_processes():
                return True

        return False
            
class Subscriber():
    
    def __init__(self):
        pass
    
    def receive_out(self, remotename, uuid, args, lines):
        log.info("STDOUT@{} {}".format(remotename, args))
        for line in lines:
            log.info("\t {}".format(line.replace("\n","")))
    
    def receive_err(self, remotename, uuid, args, lines):
        log.error("ERROR@{} {}".format(remotename, args))
        for line in lines:
            log.error("\t {}".format(line.replace("\n","")))
    
    def receive_status(self, remotename, uuid, args, exitcode):
        log.debug("EXIT {} - {}@{} {}".format(uuid, args, remotename, exitcode))
        if exitcode > 0:
            log.error("ERROR@{} : Nonzero exitcode {} by {}".format(remotename, exitcode, args))

