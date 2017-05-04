from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import  SSHException, BadHostKeyException
import logging
import traceback
import uuid
import signal
import socket

log = logging.getLogger(__name__)


BUFFSIZE = 1024


class Remote():
    def __init__(self, name, remote_host, remote_user, keyfile = None, remote_password = None, port = 22):
        self.name = name
        self.host = remote_host
        self.user = remote_user
        
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.connected = False
        
        try:
            self.ssh.connect(self.host, port, remote_user, remote_password, key_filename = keyfile, look_for_keys=True)
            self.connected = True
        
        except BadHostKeyException as e:
            raise
        except SSHException as e:
            raise
        except Exception as e:
            raise
        
        self.processes = []
        
    
    def popen(self, args, listener, wd = None, sudo = False, listen_output = False, listen_error = True, listen_status = True):
        """
        start a new process
        :param args a list of the command and its arguments
        :listener an instance of output listener to receive the out/err and status updates
        """
        assert(self.connected)
        assert(len(args) > 0)
        
        env = {}
        
        cmd = []
        if wd is not None:
            cmd.extend(["cd", wd,"&&"])
        cmd.extend(args)
        command = str.join(" ",cmd)
        
        assert(command != "")
        
        chan = self.ssh.get_transport().open_channel("session")
        chan.setblocking(0)
        
        chan.exec_command(command)
        p = Process(chan)
        
        p.listeners.append((listener, listen_output, listen_error, listen_status))
        p.set_args(args)


        self.processes.append(p)
        
        log.info("Started %s @ %s with UUID:%s via %s" %(command, self.name, p.uuid, p.chan))
        
        return p
    
    def get_process(self, uuid):
        for process in self.processes:
            if process.uuid == uuid:
                return process
            
        return None
    
    def check_processes(self):
        for process in self.processes:
            if process.exitcode != None:
                continue
            
            try:
                (out, err, exited, exitcode) = process.read_outputs()
                
                for listener, wants_output, wants_error, wants_status in process.listeners:
                    if wants_output and len(out) > 0:
                        listener.receive_out(self.name, process.uuid, out)
                    if wants_error and len(err) > 0:
                        listener.receive_err(self.name, process.uuid, err)
                    if wants_status and exited:
                        listener.receive_status(self.name, process.uuid, exitcode)
            
            except:
                traceback.print_exc()
            
            
    def kill(self, uuid):
        process = None
        for p in self.processes:
            if p.uuid == uuid:
                process = p
                break
                
        
        if process is None:
            return False
        
        else:
            process.kill()
            return True
        
    def shutdown(self):
        for process in self.processes:
            if process.exitcode == None:
                process.kill()
                process.chan.close()
                
            
        self.ssh.close()





class Process():
    def __init__(self, channel):
        self.uuid = uuid.uuid1().__str__()
        self.alive = True
        self.chan = channel
        self.args = None
        self.listeners = []
        self.stdout = []
        self.stderr = []
        self.exitcode = None
    
    def set_args(self, args):
        self.args = args    
            
    def kill(self):
        self.chan.write(signal.SIGINT)
            
    def _read_stdout(self, drain):
        
        scratch = ""
        
        try:
            if drain or self.chan.recv_ready(): 
                read = self.chan.recv(BUFFSIZE)
                
                while len(read) > 0:
                    log.debug(read)
                    scratch += read.decode("utf-8")
                    read = self.chan.recv(BUFFSIZE)
                
        except socket.timeout:
            pass
        
        return scratch.splitlines()
    
    def _read_stderr(self, drain):
        
        scratch = ""
        
        try:
            if drain or self.chan.recv_stderr_ready(): 
                read = self.chan.recv_stderr(BUFFSIZE)
                
                while len(read) > 0:
                    scratch += read.decode("utf-8")
                    read = self.chan.recv_stderr(BUFFSIZE)
                
        except socket.timeout:
            pass
        
        return scratch.splitlines()
    
    def _read_liveness(self):
        if self.chan.exit_status_ready():
            exitcode = self.chan.recv_exit_status()
            self.exitcode = exitcode
            
            self.alive = False
            return True, exitcode
        
        else:
            return False, None
        
        
    def read_outputs(self):
        log.debug("%s checking" %self.uuid)
        (exited, exitcode) = self._read_liveness()
        
        out = self._read_stdout(exited)
        err = self._read_stderr(exited)
        
        
        log.info("%s:\n-- stdout:%s\n-- stderr:%s" %(self.uuid, out, err))
        
        self.stdout.extend(out)
        self.stderr.extend(err)
        
        return out, err, exited, exitcode
        
