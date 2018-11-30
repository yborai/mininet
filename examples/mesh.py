#!/usr/bin/python

"""
cpu.py: test iperf bandwidth for varying cpu limits

Since we are limiting the hosts (only), we should expect the iperf
processes to be affected, as well as any system processing which is
billed to the hosts.

We reserve >50% of cycles for system processing; we assume that
this is enough for it not to affect results. Hosts are limited to
40% of total cycles, which we assume is enough to make them CPU
bound.

As CPU performance increases over time, we may have to reduce the
overall CPU allocation so that the host processing is still CPU bound.
This is perhaps an argument for specifying performance in a more
system-independent manner.

It would also be nice to have a better handle on limiting packet
processing cycles. It's not entirely clear to me how those are
billed to user or system processes if we are using OVS with a kernel
datapath. With a user datapath, they are easier to account for, but
overall performance is usually lower.

Although the iperf client uses more CPU and should be CPU bound (?),
we measure the received data at the server since the client transmit
rate includes buffering.
"""
import time
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.topolib import TorusTopo
from mininet.topo import Topo
from mininet.util import custom, waitListening
from mininet.log import setLogLevel, info


def bwtest( cpuLimits, k_list, period_us=100000, seconds=10 ):
    """Example/test of link and CPU bandwidth limits
       cpu: cpu limit as fraction of overall CPU time"""

    times = []
    results = {}

    for sched in 'rt', 'cfs':
        info( '*** Testing with', sched, 'bandwidth limiting\n' )
        for cpu in range(len(cpuLimits)):
            topo = MeshTopo(switchnum=k_list[cpu])
            # cpu is the cpu fraction for all hosts, so we divide
            # it across two hosts
            host = custom( CPULimitedHost, sched=sched,
                           period_us=period_us,
                           cpu=cpuLimits[cpu]*.5 )
            try:
                net = Mininet( topo=topo, host=host )
            # pylint: disable=bare-except
            except:
                info( '*** Skipping scheduler %s\n' % sched )
                break
            net.start()
            start = time.time()
            net.pingAll()
            end = time.time()
            hosts = [ net.getNodeByName( h ) for h in topo.hosts() ]
            client, server = hosts[ 0 ], hosts[ -1 ]
            info( '*** Starting iperf with %d%% of CPU allocated to hosts\n' %
                  ( 100.0 * cpuLimits[cpu] ) )
            # We measure at the server because it doesn't include
            # the client's buffer fill rate
            popen = server.popen( 'iperf -yc -s -p 5001' )
            waitListening( client, server, 5001 )
            # ignore empty result from waitListening/telnet
            popen.stdout.readline()
            client.cmd( 'iperf -yc -t %s -c %s' % ( seconds, server.IP() ) )
            result = popen.stdout.readline().split( ',' )
            bps = float( result[ -1 ] )
            popen.terminate()
            net.stop()
            updated = results.get( sched, [] )
            updated += [ ( cpuLimits[cpu], bps ) ]
            results[ sched ] = updated
            times.append(end - start)
            print(end - start)

    return results, times


def dump( results ):
    "Dump results"

    fmt = '%s\t%s\t%s\n'

    info( '\n' )
    info( fmt % ( 'sched', 'cpu', 'received bits/sec' ) )

    for sched in sorted( results.keys() ):
        entries = results[ sched ]
        for cpu, bps in entries:
            pct = '%d%%' % ( cpu * 100 )
            mbps = '%.2e' % bps
            info( fmt % ( sched, pct, mbps ) )


class MeshTopo(Topo):
    "Demo Setup"

    def __init__( self, switchnum=3, enable_all = True ):
        "Create custom topo."

        Topo.__init__( self )

        # Init values
        switches = switchnum   # total switchs
        cons = switchnum        # connections with next switch
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


if __name__ == '__main__':
    setLogLevel( 'info' )
    # These are the limits for the hosts/iperfs - the
    # rest is for system processes
    limits = [ .25, .0625, .015 ]
    k = [ 4, 16, 64 ]
    out, times = bwtest( limits, k )
    dump( out )
    print(times)
