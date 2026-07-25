from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.topology import event
from ryu.topology.api import get_switch, get_link
import networkx as nx

class ShortestPathController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(ShortestPathController, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.net = nx.DiGraph()
        self.topology_api_app = self

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Install table-miss flow entry directly
        match = parser.OFPMatch() 
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=0, match=match, instructions=inst)
        datapath.send_msg(mod)

    # Priority parameter has been completely removed as requested
    def add_flow(self, datapath, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    match=match, instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, match=match, instructions=inst)
        datapath.send_msg(mod)

    # Monitor and map topology changes dynamically
    @set_ev_cls([event.EventSwitchEnter, event.EventSwitchLeave, 
                 event.EventLinkAdd, event.EventLinkDelete])
    def get_topology_data(self, ev):
        switches = get_switch(self.topology_api_app, None)
        switches_list = [switch.dp.id for switch in switches]
        self.net.add_nodes_from(switches_list)

        links = get_link(self.topology_api_app, None)
        links_list = [(link.src.dpid, link.dst.dpid, {'port': link.src.port_no}) for link in links]
        self.net.add_edges_from(links_list)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # Ignore LLDP topology discovery packets
            return

        dst = eth.dst
        src = eth.src
        dpid = datapath.id

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # Automatically discover host locations and map them into the topology graph
        if src not in self.net:
            self.net.add_node(src)
            self.net.add_edge(dpid, src, port=in_port)
            self.net.add_edge(src, dpid, port=in_port)

        # If destination MAC path is known, compute the deterministic shortest path
        if dst in self.net:
            try:
                path = nx.shortest_path(self.net, src, dst)
                if dpid in path:
                    next_node = path[path.index(dpid) + 1]
                    out_port = self.net[dpid][next_node]['port']
                else:
                    out_port = ofproto.OFPP_FLOOD
            except nx.NetworkXNoPath:
                out_port = ofproto.OFPP_FLOOD
        else:
            out_port = ofproto.OFPP_FLOOD

        actions = [parser.OFPActionOutput(out_port)]

        # Install flow rules for non-flooding actions to streamline traffic
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src) 
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, match, actions)

        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
