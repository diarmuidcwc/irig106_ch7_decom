# irig106_ch7_decom

This repo contains two applications

1. tx_ch7_pktizer.py
2. pcm_pktizer_ch7_decom.py

## tx_ch7_pktizer.py

This emulates an inetx packetizer which encapsulates a PCM frame. The PCM frame contains
Chapter7 data from a specified offset (command line argument).
The script encapsulates UDP packets with a counter inside the chapter 7 data

## pcm_pktizer_ch7_decom.py

This will capture inetx packetizer packets, decom the chapter 7 payload and retransmit the encapsulated
packets

So the generated UDP packets from tx_ch7_pktizer.py shoudl be seen at the output of the pcm_pktizer_ch7.decom.py

Run the tx on one machine and the pcm_pktizer on the decom development board

When running locally add src to PYTHONPATH

## Packet generation

Make sure the routing for the multicast packets is to the eth interface
Then to run the transmission and receiption use the following
Customise the iface to your particular machine

These commands can be run on the same machine or different machines

```
iface=enp2s0
export PYTHONPATH=src
sudo route add 235.0.0.1 dev $iface
./scripts/tx_ch7_pktizer.py --streamid 0xdc --offset 0 --bitrate 10 --interface $iface
sudo ./.venv/bin/python scripts/pcm_pktizer_ch7_decom.py  --streamid 0xdc --interface $iface
```
