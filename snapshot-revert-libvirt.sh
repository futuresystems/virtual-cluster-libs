#!/usr/bin/env bash

short_vmname="$1"
snapname="$2"


prefix=$(basename $(readlink -f .))
vmname=${prefix}_${short_vmname}

set -x
sudo virsh snapshot-revert ${vmname} ${snapname}

# syncronize the date
date
vagrant ssh ${short_vmname}  -c "sudo date -u -s '$(date -u)'"
