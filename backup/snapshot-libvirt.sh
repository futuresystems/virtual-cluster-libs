#!/usr/bin/env bash

short_vmname="$1"
shift
snapname="$1"
shift
description="$@"

prefix=$(basename $(readlink -f .))
vmname=${prefix}_${short_vmname}

set -x
sudo virsh snapshot-create-as ${vmname} ${snapname} ${description}

# syncronize the date
date
vagrant ssh ${short_vmname}  -c "sudo date -u -s '$(date -u)'"
