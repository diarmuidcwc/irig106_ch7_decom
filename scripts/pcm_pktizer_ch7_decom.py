#!/usr/bin/env python

"""
Decom ch7packets from a packetizer source

"""

import socket
import AcraNetwork.IRIG106.Chapter7 as ch7
import AcraNetwork.iNetX as ix
import logging

OFFSET_TO_INETX = 0x2A
MIN_INETX_PKT_LEN = 1000
INETX_SID = 0xDC
CH7_OFFSET = 0

logging.basicConfig(level=logging.INFO)


def main(rx_port: int):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    sock.settimeout(2)
    sock.bind(("eth0", 0x3))
    remainder = None

    eth_p = bytes()
    first_PTFR = True

    while True:
        (data, addr) = sock.recvfrom(2000)
        inetx_pkt = ix.iNetX()

        if len(data) > MIN_INETX_PKT_LEN:
            # logging.debug(f"Received data of length {len(data)} from {addr}")
            try:
                inetx_pkt.unpack(data[OFFSET_TO_INETX:])
            except Exception as e:
                # logging.debug(f"Failed to unpacket as ientx err={e}")
                pass
            else:
                logging.debug(f"Received inetx packet={repr(inetx_pkt)}")
                if inetx_pkt.streamid == INETX_SID:
                    ch7_buffer = inetx_pkt.payload[CH7_OFFSET:]
                    logging.debug(f"ch7_buf_len = {len(ch7_buffer)}")
                    ch7_pkt = ch7.PTFR()
                    ch7_pkt.length = len(ch7_buffer)
                    ch7_pkt.unpack(ch7_buffer)
                    for p, remainder, e in ch7_pkt.get_aligned_payload(first_PTFR, remainder):
                        first_PTFR = False
                        if p is not None:
                            if p.length != 0:
                                logging.debug(f"PTDP={p}")
                                if p.content == ch7.PTDPContent.FILL:
                                    logging.debug("Ignoring FILL packets")
                                elif p.fragment == ch7.PTDPFragment.COMPLETE or p.fragment == ch7.PTDPFragment.LAST:
                                    eth_p += p.payload
                                    logging.info(f"Received an ethernet packet of lenght={p.length}")
                                    sock.send(eth_p)
                                    eth_p = bytes()
                        elif remainder is not None:
                            pass


if __name__ == "__main__":
    main(3399)
