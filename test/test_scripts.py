import unittest
from scripts import tx_ch7_pktizer
import AcraNetwork.IRIG106.Chapter7 as ch7
import struct
import logging

logging.getLogger("AcraNetwork.IRIG106.Chapter7").setLevel(logging.DEBUG)
logging.getLogger("tx_ch7_pktizer").setLevel(logging.DEBUG)


class CoreTestcase(unittest.TestCase):
    def test_basic(self):
        offset = 0
        first_PTFR = True
        eth_p = bytes()
        prev_eth_count = None
        remainder = None
        count = 0
        for frame in tx_ch7_pktizer.get_pcm_frame(offset):
            ch7_pkt = ch7.PTFR()
            ch7_buffer = frame[offset:]
            ch7_pkt.length = len(ch7_buffer)
            ch7_pkt.unpack(ch7_buffer)
            count += 1
            if count > 1000:
                return

            for p, remainder, e in ch7_pkt.get_aligned_payload(first_PTFR, remainder):
                first_PTFR = False
                if p is not None:
                    if p.length != 0:
                        if p.fragment == ch7.PTDPFragment.COMPLETE or p.fragment == ch7.PTDPFragment.LAST:
                            eth_p += p.payload

                            (count,) = struct.unpack_from(">Q", eth_p, 0x2A)
                            logging.debug(f"RX payload count={count} len={len(eth_p)}")
                            if prev_eth_count is not None:
                                if prev_eth_count + 1 != count:
                                    self.assertEqual(prev_eth_count + 1, count)
                                expected_len = 18 + 20 + 8 + (count + 1) * 8
                                self.assertEqual(expected_len, len(eth_p))

                            prev_eth_count = count
                            eth_p = bytes()
