#!/usr/bin/python

from mininet.topo import Topo
from mininet.node import OVSSwitch

"""
Ref. : https://gist.github.com/lantz/7853026
OVS Bridge with Spanning Tree Protocol

Note: STP bridges don't start forwarding until
after STP has converged, which can take a while!
See below for a command to wait until STP is up.

Example:

mn -v output --custom torus2.py --switch ovs-stp --topo torus,3,3
mininet> sh time bash -c 'while ! ovs-ofctl show s1x1 | grep FORWARD; do sleep 1; done'
"""

class OVSBridgeSTP( OVSSwitch ):
    """Open vSwitch Ethernet bridge with Spanning Tree Protocol
       rooted at the first bridge that is created"""
    prio = 1000
    def start( self, *args, **kwargs ):
        OVSSwitch.start( self, *args, **kwargs )
        OVSBridgeSTP.prio += 1
        self.cmd( 'ovs-vsctl set-fail-mode', self, 'standalone' )
        #self.cmd( 'ovs-vsctl set-controller', self )
        self.cmd( 'ovs-vsctl set Bridge', self,
                  'stp_enable=true',
                  'other_config:stp-priority=%d' % OVSBridgeSTP.prio )

switches = { 'ovs-stp': OVSBridgeSTP }

class MeshTopo(Topo):
    "Demo Setup"

    def __init__( self, switchnum=3, enable_all = True ):
        "Create custom topo."

        Topo.__init__( self )

        # Init values
        switches = switchnum   # total switchs
        cons = 1        # connections with next switch
        if cons >= switches:
                cons = switches - 1
        hosts = 1      # nodes per switch

        # Create host and Switch
        # Add link :: host to switch
        for s_num in range(1,switches+1):
                switch = self.addSwitch("s%s" %(s_num))
                for h_num in range(1,hosts+1):
                        host = self.addHost("h%s" %(h_num + ((s_num - 1) * hosts)))
                        self.addLink(host,switch)

        # Add link :: switch to switch
        for src in range(1,switches+1):
                for c_num in range(1,cons+1):
                        dst = src + c_num
                        if dst <= switches:
                                print("s%s" %src,"s%s" %dst)
                                self.addLink("s%s" %src,"s%s" %dst)
                        else:
                                dst = dst - switches
                                if src - dst > cons:
                                        print("s%s" %src,"s%s" %dst)
                                        self.addLink("s%s" %src,"s%s" %dst)

topos = { 'test': ( lambda: test() ) }
