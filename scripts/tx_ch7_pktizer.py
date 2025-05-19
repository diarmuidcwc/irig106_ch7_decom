#!/usr/bin/env python

"""
Emulate packetizer packets
"""

import AcraNetwork.McastSocket as mc
import AcraNetwork.IRIG106.Chapter7 as ch7
import AcraNetwork.SimpleEthernet as eth
import AcraNetwork.iNetX as ix
import struct
import typing
import time
import logging
import socket
import argparse
import random


logging.basicConfig(level=logging.DEBUG)
VERSION = "0.1"


def auto_int(x):
    return int(x, 0)


def create_parser():
    # Argument parser
    parser = argparse.ArgumentParser(description="Emulate ch7 packetizer packets")
    # Common
    parser.add_argument("--streamid", type=auto_int, required=True, default=0xDC, help="stream ID of the inetx packet")
    parser.add_argument("--offset", type=auto_int, required=True, default=0xDC, help="stream ID of the inetx packet")
    parser.add_argument("--interface", type=str, required=False, default="eth0", help="ethernet interface")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(VERSION))

    return parser


def get_pkts() -> typing.Generator[tuple[bytes, bool], None, None]:
    ep = eth.Ethernet()
    ep.dstmac = 0x1234
    ep.srcmac = 0x5678
    ip = eth.IP()
    ip.dstip = "192.168.28.10"
    ip.srcip = "127.0.0.1"
    up = eth.UDP()
    up.dstport = 4444
    up.srcport = 5555
    count = 0

    while True:
        pkt_len = random.randint(1, 100)
        up.payload = struct.pack(f">{pkt_len}Q", *list(range(count, count + pkt_len)))
        ip.payload = up.pack()
        ep.payload = ip.pack()
        yield ep.pack(fcs=True), False


def encapsulate_inetx(buffer: bytes, streamid: int = 1, seq: int = 0) -> bytes:
    inetxp = ix.iNetX()
    inetxp.streamid = streamid
    inetxp.payload = buffer
    inetxp.sequence = seq % (2 ^ 32)
    return inetxp.pack()


def get_pcm_frame(offset_ptfr: int = 0):
    pcm_frame_len = 1024
    ptfr_len = pcm_frame_len - offset_ptfr - 4
    zero_buf = struct.pack(">B", 0) * offset_ptfr
    for ptfr in ch7.datapkts_to_ptfr(get_pkts(), ptfr_len=ptfr_len):
        pcm_frame = zero_buf + ptfr.pack()
        logging.debug(f"TX pcm_frame_len={len(pcm_frame)} ptfr_len={ptfr_len}")
        yield pcm_frame


def main(streamid: int, pcmoffset: int):
    tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pkt_count = 0
    for pcm_frame in get_pcm_frame(pcmoffset):
        inetx_payload = encapsulate_inetx(pcm_frame, streamid, pkt_count)
        print(".", end="")
        try:
            tx_socket.sendto(inetx_payload, ("235.0.0.1", 3399))
        except:
            pass
        time.sleep(1)
        pkt_count += 1


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    main(args.streamid, args.offset)
