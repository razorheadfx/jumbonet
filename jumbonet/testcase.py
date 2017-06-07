import logging
import traceback
import time
import sys
import pathlib
import subprocess
import datetime
from . import master

log = logging.getLogger(__name__)


class Local():
    
    def __init__(self, net, experiment_root):
        self.experiment_root = experiment_root
        self.run = datetime.datetime.now()
        self.to_collect = [] #(remote, filename)
        log.info("Experiment root is set to: {}".format(experiment_root))

    def mark(self, remote, filename, location):
        log.debug("Marked {} at {} for collection".format(filename, remote))
        self.to_collect.append((remote, location, filename))

    @staticmethod
    def check_scps(scps):
        """ returns True if all have a returncode, else False """
        log.debug("Checking {}".format(scps))
        for scp in scps:
            if scp.poll() is None:
                return False

        return True

    def collect(self):
        """ blocks while waiting for scp to complete"""
        p = pathlib.Path(self.experiment_root)
        if not p.exists():
            p.mkdir()
        m = p.joinpath(self.run.strftime("%y-%m-%d_%H-%M-%S"))
        m.mkdir()
        
        scps = []

        for remote, location, filename in self.to_collect:
            log.info("Collecting {} from {}@{} to {}".format(filename, remote.user, remote.host, m))
            scp = subprocess.Popen(["/usr/bin/scp", "{}@{}:{}/{}".format(remote.user, remote.host, location, filename),"{}_{}".format(remote.name, filename)],
                                   cwd="{}".format(m),
                                   stdout=subprocess.PIPE, stderr =subprocess.PIPE, stdin = None, shell=False)
            scps.append(scp)

        #returns true if all scp commands are done
        while not self.check_scps(scps):
            time.sleep(0.5)

        log.info("Collection done")

        
class Testcase(master.Subscriber):
    
    def __init__(self, allow_errors = False):
        self.allow_errors = allow_errors
        self.net = master.Master()
        self.net.mainloop()
        self.exit_handlers = {}

    def exit_handler(self, process, cmd):
        log.debug("Exit handler registered: {} : {}".format(process.uuid, cmd))
        self.exit_handlers[process.uuid] = cmd

    def receive_out(self, remotename, uuid, args, lines):
        log.info("\t {} {}".format(remotename, args))
        for line in lines:
            log.info("\t {}".format(line.replace("\n","")))
            
    def receive_err(self, remotename, uuid, args, lines):
        log.error("{} {}".format(remotename, args))
        for line in lines:
            log.error("\t {}".format(line.replace("\n","")))

        if not self.allow_errors:
            raise Exception("Terminating because of error")
            
    def receive_status(self, remotename, uuid, args, exitcode):
        log.debug("EXIT {} - {}@{} {}".format(uuid, args, remotename, exitcode))
        if exitcode > 0:
            log.error("{} : Nonzero exitcode {} by {}".format(remotename ,exitcode, args))

            if not self.allow_errors:
                self.allow_errors = True # we dont want to clutter the output
                raise Exception("Terminating because of error, shutting down")

        cmd = self.exit_handlers.get(uuid, None)
        if cmd is not None:
            log.info("Starting exit handler for: {}@{}".format(args, remotename))
            remote = self.net.remotes.get(remotename, None)
            remote.popen(cmd, self)


    def test(self):
        raise NotImplementedError("Test Main not implemented")


    def postprocess(self):
        raise NotImplementedError("Postprocessing not implemented")
    
    def run(self, postprocessing = False):
        try:
            self.test()
            if postprocessing:
                self.net.kill_all_processes()
                # triggers exit handlers
                self.postprocess()
        except:
            traceback.print_exc()
            
        self.net.shutdown()

    def stop(self, reason = ""):
        print("Terminating test {}".format(reason))
        self.net.shutdown()
        sys.exit(1)
            
if __name__ == "__main__":
    t = Testcase()
    t.run()
