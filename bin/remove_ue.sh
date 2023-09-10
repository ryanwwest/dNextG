#!/bin/bash

imsi=$1
#key=$2

if [[ $# -lt 1 ]] ; then
    echo 'usage: [ue imsi]' # [ue key]'
    exit 1
fi

sqlcmd="DELETE FROM AuthenticationSubscription WHERE ueid = $imsi;" # AND encPermanentKey = $key;"

# Add new UE subscription to 5G Core's UDM (uses MySQL)
docker exec mysql mysql -u root -plinux -D oai_db -N -B -e "$sqlcmd"

echo "Attempted to delete UE with imsi $imsi from UDM/mysql"
