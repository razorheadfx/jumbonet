#!/usr/bin/env python3

from tkinter import *
from tkinter.ttk import Treeview
import logging
from jumbonet import master
import traceback

log = logging.getLogger(__name__)
fmt = '[%(levelname)s] %(module)s.%(funcName)s - %(message)s'
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=fmt)

class TextDisplay(Text):
    #for convenience
    def clear(self):
        self.delete("1.0", END)

    def append(self, line_or_lines):
        if type(line_or_lines) is list:
            for line in line_or_lines:
                self.insert(END, line)
        else:
            self.insert(END, line_or_lines)


class GUIExample(master.Subscriber):
    def __init__(self):
        #jumbonet stuff
        self.net = master.Master()
        self.net.mainloop()
        self.output = {}  # uuid -> list of lines of output
        self.processes = {}  # uuid/iid -> remote object

        #the fugly tkinter stuff
        self.tk = Tk()
        self.input = StringVar()
        self.selection = (None, False, False) #process/remote, is_process, is_remote
        self.tv = None  # treeview
        self.dsp_global = None
        self.dsp_process = None



    def _setup(self):
        tk = self.tk
        tk.wm_title("Jumbonet GUI Example")
        tk.protocol("WM_DELETE_WINDOW", self.shutdown)

        height = 250

        # center: treeview
        self.tv = Treeview(tk)
        tv = self.tv
        tv.config(height=height)

        # treeview configuration
        tv["columns"] = ("process", "status")
        tv.column("process", width=130)
        tv.column("status", width=70)
        tv.heading("process", text="Process UUID")
        tv.heading("status", text="Status")
        tv.bind("<ButtonRelease-1>", self.row_selected)

        # right: log windows
        r_frame = Frame(tk, height=height)
        scroll = Scrollbar(r_frame)

        #the global log (top)
        self.dsp_global = TextDisplay(r_frame, width=70, height=20)
        self.dsp_global.append("Global information")

        #the process log (bottom)
        self.dsp_process = TextDisplay(r_frame, width=70, height=25)
        self.dsp_process.append("This shows output of the selected process")


        #left: entry and buttons
        self.input.set("")
        l_frame = Frame(tk, width=200, height=height)
        l = Label(l_frame, text="Start process here")
        e = Entry(l_frame, textvariable=self.input)
        buttons = Frame(l_frame)

        # buttons
        button_add = Button(buttons, text="Start", command=self.start_process)
        button_kill = Button(buttons, text="Kill", command=self.kill_process)


        # packing all of it
        # frame on left
        l.pack(side=TOP, fill=X)
        e.pack(side=TOP, fill=X)

        button_add.pack(side=LEFT)
        button_kill.pack(side=LEFT)
        buttons.pack(side=TOP, fill=X)

        # applog frame on right
        scroll.pack(side=RIGHT, fill=Y)
        self.dsp_global.pack(side=TOP, fill=X)
        self.dsp_process.pack(side=TOP, fill=X)

        # top-level pack
        l_frame.pack(side=LEFT, fill=Y, expand=False)
        tv.pack(side=LEFT, fill=Y, expand=False)
        r_frame.pack(side=LEFT, fill=Y, expand=False)

    def shutdown(self):
        self.net.shutdown()
        sys.exit(0)

    def row_selected(self, a):
        iid = self.tv.focus()
        log.debug("Selected: {}".format(iid))

        assert(iid is not None)

        # is it a remote?
        r = self.net.remotes.get(iid)
        if r is not None:
            self.selection = (r, False, True)
            return

        # is it a process?
        #the process we're already showing output from?
        if self.selection[1] and iid == self.selection[0].uuid:
            #nothing to do then
            return

        # is it another process?
        p = self.processes[iid]
        if p is not None:
            # clear the log and display whats happening on the selected process
            self.dsp_process.clear()
            lines = self.output.get(iid)
            self.dsp_process.append(lines)
            self.selection = (p, True, False)
        else:
            self.selection = (None, False, False)


    def start_process(self):
        log.debug("Selected: {}".format(self.selection))

        if not self.selection[2]:
            return

        cmd = self.input.get()

        if cmd == "type shell command here ":
            self.dsp_global.append("\nPlease type a valid shell command")
            return

        cmdargs = cmd.split(" ")
        r = self.selection[0]

        p = r.popen(cmdargs, self, listen_output=True, listen_error=True, listen_status=True)

        self.output[p.uuid] = list()
        self.processes[p.uuid] = p

        self.tv.insert(parent=self.selection[0].name, index="end", iid=p.uuid, text=cmd, values=(p.uuid, "Running"))
        self.dsp_global.append("\nStart {} as {} to {}".format(cmd, p.uuid, self.selection))

    def kill_process(self):
        if not self.selection[1]:
            return

        p = self.selection[0]

        if not p.alive:
            self.dsp_global.append("\nCannot kill {} has alread exited".format(p.uuid))
        else:
            self.dsp_global.append("\nKilling {}".format(self.selection))
            p.kill()

    def _update_process_display(self, remotename, uuid, args, lines):
        old_output = self.output.get(uuid)
        old_output.extend(lines)


        if not self.selection[1]:
            return

        # are we showing the same process already? then add them to the log
        if uuid == self.selection[0].uuid:
            self.dsp_process.append(lines)
            self.dsp_process.see(END)


    def receive_out(self, remotename, uuid, args, lines):
        self._update_process_display(remotename, uuid, args, lines)

    def receive_err(self, remotename, uuid, args, lines):
        self._update_process_display(remotename, uuid, args, lines)

    def receive_status(self, remotename, uuid, args, exitcode):
        self.dsp_global.append("\nExit {} aka {} with code".format(args, uuid, exitcode))
        self.tv.item(uuid, values=(uuid, "Exited ".format(exitcode)))


    #### these could also be used to get a nicer output for debugging complex testcases
    def add_host(self, remote):
        self.tv.insert("", END, text=remote.name, iid=remote.name, values=[], open=True)

    def add_process(self, remote, process):
        self.processes[process.uuid] = remote
        self.tv.insert(remote.name, END,  iid=process.uuid, text=" ".join(process.args), values = (process.uuid, "Running"))


if __name__ == "__main__":

    e = GUIExample()

    e._setup()

    h1 = e.net.add_remote("localhost", "127.0.0.1", "fx", keyfile="/home/fx/.ssh/ovscontrol", \
                          inband_ip="10.0.0.1", inband_mac="00:00:00:00:00:01", inband_interface="eth0")

    e.add_host(h1)

    try:
        e.tk.mainloop()

    except SystemExit:
        print("Exiting")

    except:
        traceback.print_exc()
        e.shutdown()
