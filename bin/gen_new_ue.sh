#!/bin/bash

// missing 3 digits at end, start with 032
COMMON_IMSI_START="20895"

ueconfigpath=$1
nodenum=$2

if [[ $# -le 1 ]] ; then
    echo 'usage: [path to new UE config file]'
    exit 1
fi

# Script to see already added SUPIs
# sudo docker exec mysql mysql -u root -plinux -D oai_db -N -B -e "SELECT supi FROM AuthenticationSubscription;"

# Assuming IMSI is 15 char, with random 10 char decimal after beginning string "20895"
# Assumingkey and op both completly random 32-char hexadecimal.
imsi=$COMMON_IMSI_START
imsi+=$(tr -dc 0-9 < /dev/urandom | head -c 10)
key=$(tr -dc A-F0-9 < /dev/urandom | head -c 32)
opc=$(tr -dc a-f0-9 < /dev/urandom | head -c 32)

dnn="$(echo $nodenum | tr '[1-9]' '[a-j]')dnn"
sst=$nodenum
sd=$nodenum

#TODO probably update sqn each time after I know what it is
sqncmd='{"sqn": "000000000020", "sqnScheme": "NON_TIME_BASED", "lastIndexes": {"ausf": 0}}'
sqlcmd="INSERT INTO AuthenticationSubscription (ueid, authenticationMethod, encPermanentKey, protectionParameterId, sequenceNumber, authenticationManagementField, algorithmId, encOpcKey, encTopcKey, vectorGenerationInHss, n5gcAuthMethod, rgAuthenticationInd, supi) VALUES ('$imsi', '5G_AKA', '$key', '$key', '$sqncmd', '8000', 'milenage', '$opc', NULL, NULL, NULL, NULL, '$imsi');"

# Add new UE subscription to 5G Core's UDM (uses MySQL)
docker exec mysql mysql -u root -plinux -D oai_db -N -B -e "$sqlcmd"

# Create local ue config so can be run as simulated UE.
echo "uicc0 = {
imsi = \"$imsi\";
key = \"$key\";
opc= \"$opc\";
dnn= \"$dnn\";
nssai_sst=$sst;
nssai_sd=$sd;
}
" > $ueconfigpath

echo "New Random Test UE successfully registered in 5G core, config saved to $ueconfigpath"
