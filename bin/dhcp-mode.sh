#!/bin/bash

# Interface name
IFACE="enp24s0"  # change to your actual interface

# Netplan file path
NETPLAN_FILE="/etc/netplan/01-netcfg.yaml"

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo "Please run as root (sudo)."
   exit 1
fi

show_status() {
    ip addr show "$IFACE" | grep -A2 inet
    systemctl is-active isc-dhcp-server && echo "DHCP Server is ACTIVE" || echo "DHCP Server is INACTIVE"
}

switch_to_server() {
    echo "Switching to DHCP Server mode..."

    # Stop NetworkManager if it's managing the interface
    nmcli dev set "$IFACE" managed no 2>/dev/null

    # Configure static IP in netplan
    cat > "$NETPLAN_FILE" <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    $IFACE:
      addresses: [192.168.73.1/24]
EOF

    netplan apply

    # Set interface for DHCP server
    sed -i "s/^INTERFACESv4=.*/INTERFACESv4=\"$IFACE\"/" /etc/default/isc-dhcp-server

    # Start DHCP server
    systemctl restart isc-dhcp-server
    echo "Switched to DHCP Server mode."
}

switch_to_client() {
    echo "Switching to DHCP Client mode..."

    # Stop DHCP server
    systemctl stop isc-dhcp-server

    # Configure dynamic IP in netplan
    cat > "$NETPLAN_FILE" <<EOF
network:
  version: 2
  renderer: networkd
  ethernets:
    $IFACE:
      dhcp4: true
EOF

    netplan apply

    echo "Switched to DHCP Client mode."
}

case "$1" in
  server)
    switch_to_server
    ;;
  client)
    switch_to_client
    ;;
  status)
    show_status
    ;;
  *)
    echo "Usage: sudo $0 {server|client|status}"
    ;;
esac
