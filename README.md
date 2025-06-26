# PyRig - Automated Python Ham Rig Control

Automated Amateur Radio Rig Control

## dhcp-mode.sh

This script allows Linux machines with Ethernet ports to temporaily act
as a DHCP host. This is used to initialize devices that boot from Ethernet,
such as DMR hotspots and ARDEN equipment. You can use a crossover Ethernet
cable to directly connect devices without any hub or switch. When a device is 
connected to the server, it appears with an IP address between 192.168.73.100
and 192.168.73.150.

Usage: sudo ./bin/dhcp-mode.sh |server|client|status|

Set the DHCP mode of the Ethernet interface to client, server or print the current status.
Dev

You may have to edit bin/dhcp-mode.sh to the correct name of the Ethernet
on your machine. It is currenly "enp24s0' and you can find the addresses of
devices connected to it with

sudo arp-scan --interface=enp34s0 192.168.73.0/24

## Authors

Steve Austin - KN6ORM - Coastside Amateur Radio Club

For support: info@coastsidearc.org
