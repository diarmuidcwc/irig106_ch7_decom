#!/usr/bin/env python3

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
import logging
import argparse
import typing
import struct
import threading
import queue
import sys
import os

VERSION = "0.1"
OFFSET_TO_INETX = 0x2A
OFFSET_TO_INETX_PAYLOAD = OFFSET_TO_INETX + 28
INETX_HEADER_LEN = 28
MIN_INETX_PKT_LEN = OFFSET_TO_INETX + INETX_HEADER_LEN
A72CORE1 = 4
A72CORE2 = 5

logging.basicConfig(level=logging.CRITICAL)


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
    parser.add_argument(
        "--checkwrap",
        action="store_true",
        required=False,
        default=False,
        help="Check the payload of the data received for a counter",
    )
    parser.add_argument("--version", action="version", version="%(prog)s {}".format(VERSION))

    return parser


def transmit_worker(tx_sock: socket.socket, tx_queue: queue.Queue):
    while True:
        packet = tx_queue.get()
        if packet is None:
            break  # Poison pill to stop the thread
        try:
            tx_sock.send(packet)
        except Exception as e:
            logging.error("TX error:", e)


class MinimaliNetX(object):
    def __init__(self):
        self.streamid: int = None
        self.sequence: int = None
        self.control: int = None

    def unpack(self, buffer: bytes):
        (self.control, self.streamid, self.sequence) = struct.unpack_from(">III", buffer)
        if self.control != 0x1100_0000:
            raise Exception("Not an inetx packet")

    def __repr__(self):
        return f"Streamid={self.streamid:#0X} Sequence={self.sequence}"


def main(streamid: int, device: str, offset: int, length: typing.Optional[int], checkwrap: bool):

    # Transmit queue and socket
    tx_queue = queue.Queue(maxsize=500)
    tx_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    tx_sock.bind((device, 0))
    tx_thread = threading.Thread(target=transmit_worker, args=(tx_sock, tx_queue), daemon=True)
    tx_thread.start()

    # Receive socket
    rx_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    rx_sock.settimeout(None)
    rx_sock.bind((device, 0x3))

    # core of app
    remainder = None
    prev_seq = None
    prev_eth_count = None
    pkt_count = 0
    drop_pkt_count = 0
    golay = ch7.Golay.Golay()

    eth_p = bytes()
    first_PTFR = True

    # Define the slice of interest from the data
    if length is not None:
        ch7_slice = slice(OFFSET_TO_INETX_PAYLOAD + offset * 2, (OFFSET_TO_INETX_PAYLOAD + offset + length) * 2)
    else:
        ch7_slice = slice(OFFSET_TO_INETX_PAYLOAD + offset * 2, None)

    try:
        while True:
            (data, addr) = rx_sock.recvfrom(2000)
            inetx_pkt = MinimaliNetX()

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
                            drop_pkt_count += 1
                            logging.error(f"Dropped a packet at inetx level. Prev={prev_seq}, Cur={inetx_pkt.sequence}")

                    prev_seq = inetx_pkt.sequence

                    # logging.debug(f"Received inetx packet={repr(inetx_pkt)}")
                    if inetx_pkt.streamid == streamid:
                        ch7_buffer = data[ch7_slice]
                        # logging.debug(f"ch7_buf_len = {len(ch7_buffer)}")
                        ch7_pkt = ch7.PTFR(golay)
                        ch7_pkt.length = len(ch7_buffer)
                        ch7_pkt.unpack(ch7_buffer)
                        for p, remainder, e in ch7_pkt.get_aligned_payload(first_PTFR, remainder):
                            first_PTFR = False
                            if p is not None:
                                if p.length != 0:
                                    # logging.debug(f"PTDP={p}")
                                    if p.content == ch7.PTDPContent.FILL:
                                        pass
                                        # logging.debug("Ignoring FILL packets")
                                    elif p.fragment == ch7.PTDPFragment.COMPLETE or p.fragment == ch7.PTDPFragment.LAST:
                                        eth_p += p.payload
                                        # logging.debug(f"Sending an ethernet packet of length={p.length}")
                                        pkt_count += 1
                                        # Get rid of this check
                                        if len(eth_p) > 50 and checkwrap:
                                            (count,) = struct.unpack_from(">Q", eth_p, 0x2A)
                                            if prev_eth_count is not None:
                                                if prev_eth_count + 1 != count:
                                                    logging.error(
                                                        f"Encapsulated packet dropp. Prev={prev_eth_count} current={count}"
                                                    )

                                            prev_eth_count = count
                                        if pkt_count % 5000 == 0:
                                            print(f"{pkt_count:10,d} pkts rx {drop_pkt_count:10,d} pkts dropped")
                                        elif pkt_count % 100 == 0:
                                            print(".", end="")

                                        try:
                                            tx_queue.put_nowait(eth_p)
                                        except Exception as e:
                                            logging.error("TX queue full, dropping packet")
                                        eth_p = bytes()
                            elif remainder is not None:
                                pass
    except KeyboardInterrupt:
        logging.info("Shutting down")
    finally:
        tx_queue.put(None)
        tx_thread.join()
        rx_sock.close()
        tx_sock.close()

        return 0


if __name__ == "__main__":
    try:
        os.sched_setaffinity(0, {A72CORE1, A72CORE2})
    except Exception as e:
        logging.error(f"Failed to run onm the A72 core")
    else:
        logging.info("Running on A72 Core")
    parser = create_parser()
    args = parser.parse_args()
    ret = main(args.streamid, args.interface, args.offset, args.length, args.checkwrap)
    sys.exit(ret)
