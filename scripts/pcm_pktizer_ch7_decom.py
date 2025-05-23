#!/usr/bin/env python

"""
Decom ch7packets from a packetizer source

The assumption is that the incoming packet is an inetx packetizer packet
The payload is the PCM frame

The command line options can specify the incoming inetx stream id, the offset into the
pcm frame to the start of the ch7 data and then, optionally, the length of the ch7 data

The script will unpack the data, extract the ethernet packlets and retransmit them

"""

import socket
import AcraNetwork.IRIG106.Chapter7 as ch7
import AcraNetwork.iNetX as ix
import logging
import argparse
import typing
import struct

VERSION = "0.1"
OFFSET_TO_INETX = 0x2A
INETX_HEADER_LEN = 28
MIN_INETX_PKT_LEN = OFFSET_TO_INETX + INETX_HEADER_LEN


logging.basicConfig(level=logging.INFO)


def auto_int(x):
    return int(x, 0)


def create_parser():
    # Argument parser
    parser = argparse.ArgumentParser(description="Extract ch7 payload and retransmit")
    # Common
    parser.add_argument("--streamid", type=auto_int, required=True, default=0xDC, help="stream ID of the inetx packet")
    parser.add_argument(
        "--offset",
        type=int,
        required=False,
        default=0,
        help="Offset in words to the start of the ch7 data in the pcm payload",
    )
    parser.add_argument(
        "--length",
        type=int,
        required=False,
        default=None,
        help="Length of the ch7 data in the pcm payload in words. Leave out to select the rest of the PCM payload",
    )
    parser.add_argument("--interface", type=str, required=False, default="eth0", help="ethernet interface")
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(VERSION))

    return parser


def main(streamid: int, device: str, offset: int, length: typing.Optional[int]):
    sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    sock.settimeout(None)
    sock.bind((device, 0x3))
    remainder = None
    prev_seq = None
    prev_eth_count = None

    eth_p = bytes()
    first_PTFR = True

    if length is not None:
        ch7_slice = slice(offset * 2, (offset + length) * 2)
    else:
        ch7_slice = slice(offset * 2, None)

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
                if prev_seq is not None:
                    if prev_seq + 1 != inetx_pkt.sequence:
                        logging.error(f"Dropped a packet at inetx level. Prev={prev_seq}, Cur={inetx_pkt.sequence}")

                prev_seq = inetx_pkt.sequence

                logging.debug(f"Received inetx packet={repr(inetx_pkt)}")
                if inetx_pkt.streamid == streamid:
                    ch7_buffer = inetx_pkt.payload[ch7_slice]
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
                                    logging.debug(f"Sending an ethernet packet of length={p.length}")
                                    print(".", end="")
                                    (count,) = struct.unpack_from(">Q", eth_p, 0x2A)
                                    if prev_eth_count is not None:
                                        if prev_eth_count + 1 != count:
                                            logging.error(
                                                f"Encapsulated packet dropp. Prev={prev_eth_count} current={count}"
                                            )
                                            exit()
                                    prev_eth_count = count
                                    sock.send(eth_p)
                                    eth_p = bytes()
                        elif remainder is not None:
                            pass


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    main(args.streamid, args.interface, args.offset, args.length)
