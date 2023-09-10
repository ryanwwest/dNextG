#!/bin/bash
set -eo pipefail

STATUS=0
SGW_PORT_FOR_S1U_S12_S4_UP=2152
SGW_PORT_FOR_SX=8805
SGW_IP_S1U_INTERFACE=$(ifconfig $SGW_INTERFACE_NAME_FOR_S1U_S12_S4_UP | grep inet | awk {'print $2'})
SGW_IP_SX_INTERFACE=$(ifconfig $SGW_INTERFACE_NAME_FOR_SX | grep inet | awk {'print $2'})
S1U_S12_S4_UP_PORT_STATUS=$(netstat -unpl | grep -o "$SGW_IP_S1U_INTERFACE:$SGW_PORT_FOR_S1U_S12_S4_UP")
SX_PORT_STATUS=$(netstat -unpl | grep -o "$SGW_IP_SX_INTERFACE:$SGW_PORT_FOR_SX")
#Check if entrypoint properly configured the conf file and no parameter is unset (optional)
NB_UNREPLACED_AT=`cat /openair-spgwu/etc/*.conf | grep -v contact@openairinterface.org | grep -c @ || true`

# RWW changes
set +eo pipefail
# look at spgwu log (always pid 0). -q option isn't just silent - it exits immediately with 0 if found
# timeout 11 since printouts are every 10 seconds
timeout 11 cat /proc/1/fd/1 | grep -q 'Got successful response from NRF'
if [ $? -ne 0 ]; then
       STATUS=1
       echo "Healthcheck error: No 'Got successful response from NRF' heartbeat log output detected"
else
       echo "NRF heartbeat detected"
fi
set -eo pipefail


if [ $NB_UNREPLACED_AT -ne 0 ]; then
        STATUS=1
        echo "Healthcheck error: UNHEALTHY configuration file is not configured properly"
fi

if [[ -z $S1U_S12_S4_UP_PORT_STATUS ]]; then
        STATUS=1
        echo "Healthcheck error: UNHEALTHY S1U port $SGW_PORT_FOR_S1U_S12_S4_UP is not listening."
fi

if [[ -z $SX_PORT_STATUS ]]; then
        STATUS=1
        echo "Healthcheck error: UNHEALTHY SX port $SGW_PORT_FOR_SX is not listening."
fi

exit $STATUS
