import logging

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.link import TCLink
from mininet.log import setLogLevel
from mininet.cli import CLI
from mininet.node import RemoteController

import json
k = 16
peer_switch2host_num = 1
"""
pod的数量为        k                  16
交换机总数      5*(k/2)^2       5*(16/2)^2 = 320
核心交换机数量为 (k/2)^2         (16/2)^2 = 64
每个pod分为两层，每层2(k/2)^2 个交换机，
上层称为汇聚层   128
下层称为接入层   128
"""
switch2host = dict()
ip2host = dict()


def fattree(k, peer_switch2host_num=1):
    # Create FatTree topology
    fattree_topo = Topo()
    n_core = (k // 2) ** 2
    n_aggr = k * k // 2
    n_edge = n_aggr
    pod = k
    all_switch_num = n_core + n_aggr + n_edge
    # Starting create the switch
    core_switch = []  # core switch
    aggregate_switch = []  # aggregate switch
    edge_switch = []  # edge switch
    # Create core switches
    for i in range(1, int(n_core) + 1):
        c_sw = fattree_topo.addSwitch('c{}'.format(i), dpid='c' + str(i))
        core_switch.append(c_sw)
    # Create aggregation switches
    for i in range(1, int(n_aggr) + 1):
        a_sw = fattree_topo.addSwitch('a{}'.format(i), dpid='a' + str(i))
        aggregate_switch.append(a_sw)
    # Create edge switches
    for i in range(1, int(n_edge) + 1):
        e_sw = fattree_topo.addSwitch('e{}'.format(i), dpid='e' + str(i))
        edge_switch.append(e_sw)
        switch2host['e' + str(i)] = []
    # Connect core switches to aggregation switches
    for i in range(n_core):
        c_sw = core_switch[i]
        start = i % (k // 2)
        for j in range(k):
            fattree_topo.addLink(c_sw, aggregate_switch[start + j * (pod // 2)], cls=TCLink, bw=30)
    # Connect aggregation switches to edge switches
    for i in range(n_aggr):
        group = i // (pod // 2)
        for j in range(pod // 2):
            fattree_topo.addLink(aggregate_switch[i], edge_switch[group * (pod // 2) + j], cls=TCLink, bw=20)
    # Create hosts and connect them to edge switches
    for i in range(n_edge):
        for j in range(1, peer_switch2host_num + 1):
            n = i * peer_switch2host_num + j
            if n < 16:
                mac = '00:00:00:00:01:0{}'.format(hex(n).split('x')[1])
                ip = '10.0.0.{}'.format(n)
                host = fattree_topo.addHost('h{}'.format(n), ip=ip, mac=mac, cpu=0.5)
            elif n < 256:
                ip = '10.0.0.{}'.format(n)
                mac = '00:00:00:00:01:{}'.format(hex(n).split('x')[1])
                host = fattree_topo.addHost('h{}'.format(n), ip=ip, mac=mac, cpu=0.5)
            else:
                ip = '10.0.1.{}'.format(n >> 8)
                mac = '00:00:00:00:02:0{}'.format(hex(n >> 8).split('x')[1])
                host = fattree_topo.addHost('h{}'.format(n), ip=ip, mac=mac, cpu=0.5)
            fattree_topo.addLink(edge_switch[i], host, cls=TCLink, bw=10)
            switch2host['e' + str(i + 1)].append('h' + str(n))
            ip2host[ip] = host

    data = dict()
    data['switch2host'] = switch2host
    data['ip2host'] = ip2host
    data['all_switch_num'] = all_switch_num
#    with open("../config/record.json", "w") as f:
#        json.dump(data, f)

    # Add Controllers
    co0 = RemoteController(name='co0', ip='127.0.0.1', port=6633)
    co1 = RemoteController(name='co1', ip='127.0.0.1', port=6634)
    net = Mininet(topo=fattree_topo, link=TCLink, controller=co0)
    net.addController(co1)
    net.start()
    for switch in net.switches:
        switch.cmd('ovs-vsctl set bridge {} rstp_enable=true'.format(switch.name))
    # Wait for controller to update paths in network
    print("Please open controller")
    net.waitConnected()
    # net.pingAll(3)
    # Run traffic generator script
    CLI(net)

    for host in net.hosts:
        print(host)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    fattree(k, peer_switch2host_num)

