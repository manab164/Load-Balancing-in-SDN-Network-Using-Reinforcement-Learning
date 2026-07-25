from mininet.topo import Topo

class TreeTopo(Topo):

    def build(self):

        # Switches
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
        s5 = self.addSwitch('s5')
        s6 = self.addSwitch('s6')

        # Hosts
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        # Tree Structure

        self.addLink(s1, s2)
        self.addLink(s1, s3)

        self.addLink(s2, s4)
        self.addLink(s2, s5)

        self.addLink(s3, s6)

        # Hosts

        self.addLink(h1, s4)
        self.addLink(h2, s5)
        self.addLink(h3, s6)
        self.addLink(h4, s6)

topos = {'tree_topo': (lambda: TreeTopo())}

