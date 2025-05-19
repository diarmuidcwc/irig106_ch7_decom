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


logging.basicConfig(level=logging.DEBUG)


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
        up.payload = struct.pack(">100Q", *list(range(count, count + 100)))
        ip.payload = up.pack()
        ep.payload = ip.pack()
        yield ep.pack(fcs=True), False


def encapsulate_inetx(buffer: bytes, seq: int = 0) -> bytes:
    inetxp = ix.iNetX()
    inetxp.streamid = 0xDC
    inetxp.payload = buffer
    inetxp.sequence = seq
    return inetxp.pack()


def get_pcm_frame():
    pcm_frame_len = 1024
    offset_ptfr = 0
    ptfr_len = pcm_frame_len - offset_ptfr - 4
    zero_buf = struct.pack(">B", 0) * offset_ptfr
    for ptfr in ch7.datapkts_to_ptfr(get_pkts(), ptfr_len=ptfr_len):
        pcm_frame = zero_buf + ptfr.pack()
        logging.debug(f"TX pcm_frame_len={len(pcm_frame)} ptfr_len={ptfr_len}")
        yield pcm_frame


def main():
    tx_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for pcm_frame in get_pcm_frame():
        inetx_payload = encapsulate_inetx(pcm_frame)
        print(".", end="")
        try:
            tx_socket.sendto(inetx_payload, ("235.0.0.1", 3399))
        except:
            pass
        time.sleep(1)


if __name__ == "__main__":
    main()
