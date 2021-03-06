from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import  SSHException, BadHostKeyException
import logging
import traceback
import uuid
import socket

log = logging.getLogger(__name__)

BUFFSIZE = 1024


class Remote():
    def __init__(self, name, remote_host, remote_user, keyfile = None, remote_password = None, \
                 port = 22, inband_interface = None, inband_ip = None, inband_mac = None, cmd_factory = None):
        self.name = name
        self.user = remote_user
        self.host = remote_host
        self.port = port
        
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.connected = False

        self.inband_interface = inband_interface
        self.inband_ip = inband_ip
        self.inband_mac = inband_mac
        self.cmds = cmd_factory
        
        try:
            self.ssh.connect(self.host, port, remote_user, remote_password, key_filename = keyfile, look_for_keys=True)
            self.connected = True
            self.ssh.get_transport().set_keepalive(1)
        
        except BadHostKeyException as e:
            raise
        except SSHException as e:
            raise
        except Exception as e:
            raise
        
        self.processes = []
        
    def IP(self):
        return self.inband_ip
        
        
    def MAC(self):
        return self.inband_mac

    def Iface(self):
        return self.inband_interface
        
    
    def popen(self, args, listener, wd = None, listen_output = False, listen_error = True, listen_status = True):
        """
        start a new process
        :param args a list of the command and its arguments
        :listener an instance of output listener to receive the out/err and status updates
        """
        assert(self.connected)
        assert(len(args) > 0)
        
        cmd = []
        if wd is not None:
            cmd.extend(["cd", wd,"&&"])
        cmd.extend(args)
        command = str.join(" ",cmd)
        
        assert(command != "")
        
        chan = self.ssh.get_transport().open_channel("session")
        chan.setblocking(0)
        chan.get_pty()

        chan.exec_command(command)
        p = Process(chan, args)
        
        p.listeners.append((listener, listen_output, listen_error, listen_status))


        self.processes.append(p)
        
        log.debug("Started %s @ %s with UUID:%s via %s" %(command, self.name, p.uuid, p.chan))
        
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
                        listener.receive_out(self.name, process.uuid, process.args, out)
                    if wants_error and len(err) > 0:
                        listener.receive_err(self.name, process.uuid, process.args, err)
                    if wants_status and exited:
                        listener.receive_status(self.name, process.uuid, process.args, exitcode)
            
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

    def killall(self):
        for p in self.processes:
            p.kill()
        
    def shutdown(self):
        for process in self.processes:
            if process.exitcode == None:
                process.kill()
                process.chan.close()
                
            
        self.ssh.close()

    def has_running_processes(self):
        for p in self.processes:
            if p.alive:
                return True

        return False





class Process():
    def __init__(self, channel, args):
        self.uuid = uuid.uuid1().__str__()
        self.args = args
        self.alive = True
        self.chan = channel
        self.listeners = []
        self.stdout = []
        self.stderr = []
        self.exitcode = None
        log.debug("New Process: %s as %s via %s" %(self.args, self.uuid, self.chan))

    def __str__(self):
        return "Process {}:{} alive: {} via {}, listeners: {}, exitcode: {}".format(self.uuid, self.args, self.alive, self.chan, self.listeners, self.exitcode)

    def kill(self):
        self.chan.close()
            
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
        
        
        log.debug("%s:\n-- stdout:%s\n-- stderr:%s" %(self.uuid, out, err))
        
        self.stdout.extend(out)
        self.stderr.extend(err)
        
        return out, err, exited, exitcode
        
