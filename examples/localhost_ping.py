import logging
from jumbonet import testcase
import getpass
import os
import time
import sys

log = logging.getLogger(__name__)
frm = "[%(levelname)s] %(module)s.%(funcName)s - %(message)s"
logging.basicConfig(stream=sys.stdout, level = logging.INFO, format = frm)

class Example(testcase.Testcase):

    def test(self):
        net = self.net
        path_to_keyfile = None
        ssh_port = 22

        print("This example will:  \n - connect to localhost:22 using ssh \n - run ping localhost for 20 s \n - cut the ping short after 10 \n - disconnect")
        print("Normally this would be done using public/private keypair but here we use your password")
        input("Continue?")

        remote_username = os.environ["USER"]

        if path_to_keyfile is None:
            remote_pw = getpass.getpass("Enter the password for {}@localhost, please\n".format(remote_username))

        print("1.Connecting Hosts \n")
        print("\t Under the hood jumbonet uses paramiko to handle the ssh part")

        h1 = net.add_remote("localhost", "127.0.0.1", remote_username, remote_password=remote_pw, keyfile=path_to_keyfile, \
                            inband_ip = "10.0.0.1", inband_mac = "00:00:00:00:00:01", inband_interface="eth0")

        print("2.Running Test \n")
        print("\t You could also unsubscribe from stdout, stderr or status updates.")
        ping = h1.popen(["ping", "localhost","-c","20"], self, listen_output=True, listen_error=True, listen_status=True)
        # this would run for 20s but we're gonna kill the whole thing after 10 secs
        # we could also register an exit to run after a process exits or gets killed
        # i.e. self.exit_handler(ping, ["foo","bar"])
        time.sleep(10)

        print("3.Exiting/Killing Processes \n")
        print("\t Exit handlers would run now")

    def postprocess(self):
        print("(4).Postprocessing")
        print("\t You could implement some postprocessing ... data collection for example")
        print("\t Check out jumbonet.testcase.Local if you want to collect files from the remotes to a certain folder using scp")
            
if __name__ == "__main__":
    t = Example(allow_errors=False)
    #this will exit and disconnect all remotes if an exception happens within test() or postprocess()
    #Ctrl-C works to stop prematurely
    t.run(postprocessing=True)
