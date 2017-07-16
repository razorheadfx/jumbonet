# jumbonet  
network experiment scripting for hardware testbeds

### What is jumbonet?  
__TL;DR__ A python network experiment runner for physical network testbeds inspired by the awesome [mininet network emulator](http://mininet.org/)  
  
If you are familiar with mininet, you know how easy it is to create a virtual network and run experiments using its Python2 API.  
Jumbonet aims for a similar experience when scripting experiments on "pyhsical" network testbeds consisting of multiple host machines and real switches.  
Hosts ("remotes" in jumbonet terms) are connected via SSH using the paramiko SSH library. This done either using password authentication (not recommended) or public/private keys (e.g. added via _ssh-copy-id_ beforehand). Once connected, remotes can be used like mininet hosts, to the extend that whole mininet scripts can be copy-pasted to jumbonet (with minor changes). 

In jumbonet stdout and stderr are handled through callbacks instead of Popen, which allows for tighter error handling within the script and the experiment development/debugging process across all the involved hosts.

Check out the examples to learn more.

### Comparison of Jumbonet & Mininet
Consider the following excerpt from a low-level mininet script.  
  
```python
...

net = Mininet( topo=None, build=False, ipBase='10.0.0.0/8')
h1 = net.addHost('h1', cls=Host, ip='10.0.0.1', mac = "00:00:00:00:00:01")
h2 = net.addHost('h2', cls=Host, ip='10.0.0.2', mac = "00:00:00:00:00:02")

# add some switches and connect the hosts
...

net.start()

# let the hosts ping each other
ping1 = h1.popen(["ping",h2.IP()])
ping2 = h2.popen(["ping",h1.IP()])

# let it run for 10 secs
time.sleep(10)

# kill the processes
ping1.kill()
ping2.kill()

# destroy the net
net.stop()

```
  
The same in jumbonet:
```python

from jumbonet import master

net = master.Master()
net.mainloop()

h1 = net.add_remote("h1", "username", "20.0.0.1", keyfile = "~/.ssh/id_rsa", \
	inband_ip = "10.0.0.1", inband_mac = "00:00:00:00:00:01", inband_interface = "eth0")
h2 = net.add_remote("h2", "another_username", "domain.hostname", keyfile = "~/path/to/another/keyfile", \ 
	inband_ip = "10.0.0.2", inband_mac = "00:00:00:00:00:02", inband_interface = "eno1")

# if any of these cannot connect an exception will be thrown
# if you create the net with net = master.Master(default_keyfile = "/path/to/keyfile", \
#						default_user = "username_for_many_hosts", default_inband_interface = "eno1")
# you could use the mininet-like way of creating a host:
# h3 = net.addHost("name", "ip", "mac", remote_host = "name.or.ip.of.the.host")

# lets say your hosts have a way of talking to each other

ping1 = h1.popen(["ping", h2.IP()], self, \
		listen_output = False, listen_error = False, listen_error = False)
ping2 = h2.popen(["ping", h1.IP()], self, \
		listen_output = False, listen_error = False, listen_error = False)

# ping1 and ping2 are instances of jumbonet.remote.Process, which wraps the SSHChannel, the process on the remote end and it's stdout/stderr output
		
# the reference to self and the bools for the listeners are necessaryto handle the callbacks on stdout, stderr and status change
# the easiest way to handle these is to extend master.Subscriber in your class and overload its methods to your liking
# here the output is discarded for simplicity's sake (i.e. listen_output = False)

time.sleep(10)

ping1.kill()
ping2.kill()

print("\n".join(ping1.stdout))

net.shutdown()
# would also kill the running processes implicitly
```

For further reference check out examples/ or jumbonet/testcase, which is a versatile wrapper for more complex experiments with result post-processing on remotes and the master machine.


### Depencies & Installation
Dependencies  
* Python3
* [Paramiko](http://www.paramiko.org/)
* SSH Server on the remote bosts
  
Install  
```shell
python3 setup.py install
# should install paramiko through pip if necessary
# or run python3 setup.py develop to just link to the repo location (recommended for the examples)
```


### Known Issues / Common Errors

##### SSHD Session Limits
Most SSH Servers have a default limit on the number of concurrent ssh sessions they allow, e.g. 10 with OpenSSH on Ubuntu 14.04.  
Running many commands against one such remote will yield errors like this:
´´´
...
paramiko.transport: secsh channel 11 opened.
paramiko.transport: [chan 11] EOF received (11)
paramiko.transport: [chan 11] EOF sent (11)
...
´´´
This can be fixed by setting/adding _MaxSessions_ in /etc/ssh/sshd_config to a higher value.

 
### TODOS
- [ ] add something of a debug-gui (maybe based on the GUI Example) to the master or testcase
- [ ] revise the remote.popen  (it's a little verbose)
