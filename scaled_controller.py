from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, arp, ipv4, tcp, udp, icmp, in_proto
from ryu.lib import hub
import time
import random

class Scaled_RL_LoadBalancer(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Scaled_RL_LoadBalancer, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.arp_cache = {} 
        self.arp_table = {} 
        self.ip_cache = {} 
        self.datapaths = {}
        
       
        self.core_ports = {
            1: [3, 4],          # s1 connects to s6, s7
            2: [3, 4],          # s2 connects to s7, s8
            3: [3, 4],          # s3 connects to s8, s9
            4: [3, 4],          # s4 connects to s9, s10
            5: [3, 4],          # s5 connects to s10, s6
            6: [1, 2, 3],       # s6 connects to s1, s5, s11
            7: [1, 2, 3],       # s7 connects to s1, s2, s11
            8: [1, 2, 3],       # s8 connects to s2, s3, s12
            9: [1, 2, 3],       # s9 connects to s3, s4, s12
            10: [1, 2, 3],      # s10 connects to s4, s5, s11
            11: [1, 2, 3, 4],   # s11 connects to s6, s7, s10, s12
            12: [1, 2, 3]       # s12 connects to s8, s9, s11
        }
        self.q_table = {}     
        self.epsilon = 0.2    
        self.alpha = 0.2      
        self.gamma = 0.9
        
        self.port_stats = {} 
        self.monitor_thread = hub.spawn(self._monitor)

    def get_q_value(self, state, action):
        return self.q_table.get((state, action), 0.0)

    def choose_action(self, state, dpid, in_port):
        available_ports = [p for p in self.core_ports.get(dpid, []) if p != in_port]
        if not available_ports: 
            available_ports = self.core_ports.get(dpid, []) 
            if not available_ports:
                return ofproto_v1_3.OFPP_FLOOD
                
        dst_mac = state[2]
        if dst_mac in self.mac_to_port.get(dpid, {}):
            known_port = self.mac_to_port[dpid][dst_mac]
            if known_port in available_ports and self.get_q_value(state, known_port) == 0.0:
                self.q_table[(state, known_port)] = 0.5 
            
        if random.random() < self.epsilon:
            return random.choice(available_ports)
        
        q_values = [self.get_q_value(state, a) for a in available_ports]
        max_q = max(q_values)
        best_actions = [a for a, q in zip(available_ports, q_values) if q == max_q]
        return random.choice(best_actions)

    def _monitor(self):
        """The New Smart Dashboard"""
        while True:
            hub.sleep(5) 
            
            if self.q_table:
                current_time = time.strftime('%H:%M:%S')
                print(f"\n[{current_time}] --- NETWORK PATHS ---")
                
                # Sort ALL links mathematically (lowest/most negative penalty first)
                sorted_links = sorted(self.q_table.items(), key=lambda item: item[1])
                
                # Take exactly the top 15 to expand your dashboard
                top_15 = sorted_links[:15]
                
                for (state, action), q_val in top_15:
                    if q_val < -50.0:
                        status = "⚠️  CONGESTED"
                    else:
                        status = "✅ BALANCED "
                        
                    print(f"|| Switch {state[0]:>2} || Port {action} || Flow: {state[1]} -> {state[2]} || Score: {q_val} ")
                
                print("-" * 75)

            for dpid, dp in self.datapaths.items():
                parser = dp.ofproto_parser
                req = parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY)
                dp.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def _port_stats_reply_handler(self, ev):
        body = ev.msg.body
        dpid = ev.msg.datapath.id
        self.port_stats.setdefault(dpid, {})
        
        for stat in body:
            port = stat.port_no
            if port not in self.core_ports.get(dpid, []): continue 
            
            old_bytes = self.port_stats[dpid].get(port, 0)
            bytes_sent = stat.tx_bytes - old_bytes
            self.port_stats[dpid][port] = stat.tx_bytes 
            
            reward = -(bytes_sent / 10000.0) 
            
            for (state, action), q_val in list(self.q_table.items()):
                if state[0] == dpid and action == port: 
                    next_max = max([self.get_q_value(state, a) for a in self.core_ports[dpid]])
                    new_q = q_val + self.alpha * (reward + self.gamma * next_max - q_val)
                    self.q_table[(state, action)] = round(new_q, 2)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        self.datapaths[datapath.id] = datapath 
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority, idle_timeout=idle_timeout, match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype in [0x86dd, 0x88cc]: return

        dpid = datapath.id
        src = eth.src
        dst = eth.dst

        if eth.ethertype == 0x0800:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt:
                pkt_sig = (dpid, ip_pkt.src, ip_pkt.dst, ip_pkt.identification)
                current_time = time.time()
                if pkt_sig in self.ip_cache and (current_time - self.ip_cache[pkt_sig]) < 1.5:
                    return 
                self.ip_cache[pkt_sig] = current_time

        if eth.ethertype == 0x0806: 
            arp_pkt = pkt.get_protocol(arp.arp)
            if arp_pkt:
                self.arp_table[arp_pkt.src_ip] = src 
                
                if arp_pkt.opcode == arp.ARP_REQUEST:
                    if arp_pkt.dst_ip in self.arp_table:
                        reply_mac = self.arp_table[arp_pkt.dst_ip]
                        e = ethernet.ethernet(dst=src, src=reply_mac, ethertype=0x0806)
                        a = arp.arp(hwtype=1, proto=0x0800, hlen=6, plen=4, opcode=2,
                                    src_mac=reply_mac, src_ip=arp_pkt.dst_ip,
                                    dst_mac=src, dst_ip=arp_pkt.src_ip)
                        p = packet.Packet()
                        p.add_protocol(e)
                        p.add_protocol(a)
                        p.serialize()
                        
                        actions = [parser.OFPActionOutput(in_port)]
                        out = parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                                  in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=p.data)
                        datapath.send_msg(out)
                        return
                    else:
                        cache_key = (dpid, src, arp_pkt.dst_ip)
                        current_time = time.time()
                        if cache_key in self.arp_cache and (current_time - self.arp_cache[cache_key]) < 2.0: return 
                        self.arp_cache[cache_key] = current_time

        self.mac_to_port.setdefault(dpid, {})
        if not src.startswith('01:00:5e') and src != 'ff:ff:ff:ff:ff:ff':
            if src in self.mac_to_port[dpid]:
                old_port = self.mac_to_port[dpid][src]
                if old_port not in self.core_ports.get(dpid, []) and in_port in self.core_ports.get(dpid, []):
                    pass 
                else:
                    self.mac_to_port[dpid][src] = in_port
            else:
                self.mac_to_port[dpid][src] = in_port

        out_port = ofproto.OFPP_FLOOD
        # Default priority for "Other" traffic
        priority = 100 
        match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
        timeout = 2 

        # 1. ARP and IPv6 (Highest Priority)
        if eth.ethertype == 0x0806 or eth.ethertype == 0x86dd:
            priority = 1000
            match = parser.OFPMatch(in_port=in_port, eth_type=eth.ethertype, eth_dst=dst)
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]

        elif eth.ethertype == 0x0800:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt:
                # 1. ICMP (Highest Priority alongside ARP)
                if ip_pkt.proto == in_proto.IPPROTO_ICMP:
                    priority = 1000
                    match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_dst=dst, ip_proto=1)
                
                # 2 & 3. TCP (HTTP highest, general TCP lower)
                elif ip_pkt.proto == in_proto.IPPROTO_TCP:
                    tcp_pkt = pkt.get_protocol(tcp.tcp)
                    if tcp_pkt:
                        # Common HTTP ports: 80, 8080, and the previous 8000
                        if tcp_pkt.dst_port in [80, 8000, 8080]:
                            priority = 800
                            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_dst=dst, ip_proto=6, tcp_dst=tcp_pkt.dst_port)
                        elif tcp_pkt.src_port in [80, 8000, 8080]:
                            priority = 800
                            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_dst=dst, ip_proto=6, tcp_src=tcp_pkt.src_port)
                        else:
                            priority = 600
                            match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_dst=dst, ip_proto=6)
                
                # 4. UDP
                elif ip_pkt.proto == in_proto.IPPROTO_UDP:
                    priority = 400
                    match = parser.OFPMatch(in_port=in_port, eth_type=0x0800, eth_dst=dst, ip_proto=17)

                # RL Load-balancing lookup for routable packets (TCP/UDP)
                if ip_pkt.proto in [in_proto.IPPROTO_TCP, in_proto.IPPROTO_UDP]:
                    if dst in self.mac_to_port[dpid] and self.mac_to_port[dpid][dst] not in self.core_ports.get(dpid, []):
                        out_port = self.mac_to_port[dpid][dst]
                    else:
                        state = (dpid, ip_pkt.src, ip_pkt.dst)
                        out_port = self.choose_action(state, dpid, in_port)
                        if (state, out_port) not in self.q_table:
                            self.q_table[(state, out_port)] = 0.0
                else:
                    if dst in self.mac_to_port[dpid]:
                        out_port = self.mac_to_port[dpid][dst]
        
        else:
            if dst in self.mac_to_port[dpid]:
                out_port = self.mac_to_port[dpid][dst]

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            self.add_flow(datapath, priority, match, actions, idle_timeout=timeout)

        data = None if msg.buffer_id != ofproto.OFP_NO_BUFFER else msg.data
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
