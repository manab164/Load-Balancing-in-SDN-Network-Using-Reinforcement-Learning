from mininet.topo import Topo

class Scaled_RL_Topo(Topo):
    def build(self):
        # 1. Add 12 Switches (s1-s5 are Edge, s6-s12 are Core)
        switches = [self.addSwitch('s{}'.format(i)) for i in range(1, 13)]

        # 2. Add 10 Hosts
        hosts = [self.addHost('h{}'.format(i), ip='10.0.0.{}'.format(i)) for i in range(1, 11)]

        # 3. Connect Hosts to Edge Switches (Ports 1 & 2 on Edge Switches)
        self.addLink(hosts[0], switches[0])  # h1 -> s1
        self.addLink(hosts[1], switches[0])  # h2 -> s1
        self.addLink(hosts[2], switches[1])  # h3 -> s2
        self.addLink(hosts[3], switches[1])  # h4 -> s2
        self.addLink(hosts[4], switches[2])  # h5 -> s3
        self.addLink(hosts[5], switches[2])  # h6 -> s3
        self.addLink(hosts[6], switches[3])  # h7 -> s4
        self.addLink(hosts[7], switches[3])  # h8 -> s4
        self.addLink(hosts[8], switches[4])  # h9 -> s5
        self.addLink(hosts[9], switches[4])  # h10 -> s5

        # 4. Connect Edge to Core (Ports 3 & 4 on Edge Switches)
        self.addLink(switches[0], switches[5])  # s1 -> s6
        self.addLink(switches[0], switches[6])  # s1 -> s7
        self.addLink(switches[1], switches[6])  # s2 -> s7
        self.addLink(switches[1], switches[7])  # s2 -> s8
        self.addLink(switches[2], switches[7])  # s3 -> s8
        self.addLink(switches[2], switches[8])  # s3 -> s9
        self.addLink(switches[3], switches[8])  # s4 -> s9
        self.addLink(switches[3], switches[9])  # s4 -> s10
        self.addLink(switches[4], switches[9])  # s5 -> s10
        self.addLink(switches[4], switches[5])  # s5 -> s6 (Closes edge ring)

        # 5. Core-to-Core Deep Mesh (For optimal AI routing choices)
        self.addLink(switches[5], switches[10]) # s6 -> s11
        self.addLink(switches[6], switches[10]) # s7 -> s11
        self.addLink(switches[7], switches[11]) # s8 -> s12
        self.addLink(switches[8], switches[11]) # s9 -> s12
        self.addLink(switches[9], switches[10]) # s10 -> s11
        self.addLink(switches[10], switches[11])# s11 -> s12

topos = {'scaled_topo': (lambda: Scaled_RL_Topo())}



