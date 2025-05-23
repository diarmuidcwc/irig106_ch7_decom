# irig106_ch7_decom

When running locally add src to PYTHONPATH

## Packet generation

Make sure the routing for the multicast packets is to the eth0 interface
```
sudo route add 235.0.0.1 dev eth0
```
Then to run the transmission
```
 ./scripts/tx_ch7_pktizer.py --streamid 0xdc --offset 0 --bitrate 10
```
