#!/usr/bin/env python

"""
Decom ch7packets from a packetizer source

"""

import socket
import AcraNetwork.IRIG106.Chapter7 as ch7
import AcraNetwork.iNetX as ix
import logging
import argparse

VERSION = "0.1"
OFFSET_TO_INETX = 0x2A
INETX_HEADER_LEN = 28
CH7_OFFSET = 0
MIN_INETX_PKT_LEN = OFFSET_TO_INETX + INETX_HEADER_LEN


logging.basicConfig(level=logging.INFO)


def auto_int(x):
    return int(x, 0)


def create_parser():
    # Argument parser
    parser = argparse.ArgumentParser(description="Extract ch7 payload and retransmit")
    # Common
    parser.add_argument("--streamid", type=auto_int, required=True, default=0xDC, help="stream ID of the inetx packet")
    parser.add_argument("--interface", type=str, required=False, default="eth0", help="ethernet interface")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(VERSION))

    return parser


def main(streamid: int, device: str):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    sock.settimeout(None)
    sock.bind((device, 0x3))
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
                if inetx_pkt.streamid == streamid:
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
    parser = create_parser()
    args = parser.parse_args()
    main(args.streamid, args.interface)
