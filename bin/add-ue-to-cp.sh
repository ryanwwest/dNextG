# only works if the the core plane node (10.10.1.1) is running src/uegenapi.py
echo curling 10.10.1.1:18693/gen-ue/$2
curl -s 10.10.1.1:18693/gen-ue/$2 | sudo tee $1
echo todo fail if CPs ue add/remove api is down
