#!/bin/bash
###### sourcing the rc file to prevent any errors
. CloudComp12-openrc.sh

######## Define variable 
loadBalancer="loadBalancer1"
loadBalancerStatus="NOTACTIVE"
poolName="pool1"
listenerName="listener1"
monitorName="health-Monitor"

counter=0
limit=3
while [[ $loadBalancerStatus != "ACTIVE" ]]
do
	if [[ "$counter" -lt "$limit" ]];then
		##### Deleting the existing pools
		echo "Deleting pools.."
		poolList=$(openstack loadbalancer pool list -c id -f value)
		for pool in $poolList; do
			openstack loadbalancer pool delete $pool
		done

		######## Delete all existing load balancers
		echo "Deleting load balancers"
		lbs=$(openstack loadbalancer list -c id -f value)
		for val in $lbs; do
		    openstack loadbalancer delete --cascade --wait $val
		done
		####### Done deleting the existing load balancers

		####### Check for available subnets
		####### If CloudComp12-subnet exists user if else user the available
		subnets=$(openstack subnet list -c Name -f value)
		subnet=""
		for name in $subnets; do
			subnet=$name
		    if [[ "$name" == "" ]]; then
		    	subnet=$name
		    fi

		    if [[ "$name" == "CloudComp12-subnet" ]]; then
		    	subnet=$name
		    fi
		done

		echo "found the subnet to use ::$subnet" 
		####### create the load balancer only if a valid subnet is found
		if [[ $subnet != "" ]]; then
			######## Create a new load balancer named loadBalancer
			openstack loadbalancer create --name $loadBalancer --vip-subnet-id $subnet --wait
			loadBalancerStatus=$(openstack loadbalancer list -c provisioning_status -f value --name loadBalancer1)
		fi
		echo "Retrying to create load balancer $counter"
	fi
	
	((counter=counter+1))

	if [[ "$counter" -gt "$limit" ]];then
		echo "Exiting after retry number $counter, please the openstack environment"
		return
	fi
done


echo "Load balancer successfully created"
openstack loadbalancer show $loadBalancer
openstack loadbalancer listener delete --wait $listenerName
openstack loadbalancer listener create --name $listenerName --protocol HTTP --connection-limit 1000 --protocol-port 80 $loadBalancer
openstack loadbalancer pool create --name $poolName --lb-algorithm ROUND_ROBIN --listener $listenerName --protocol HTTP --wait
openstack loadbalancer healthmonitor create --name $monitorName --delay 5 --max-retries 4 --timeout 10 --type HTTP --url-path /healthcheck $poolName --wait

###### Check for all api instances
###### If the name contains app-api and is active add it 
instances=$(openstack server list -c Name -f value --status ACTIVE)
for node in $instances; do
	if [[ $node == *"app-api"* ]]; then
    	server=$(openstack server list -c Networks --name $node -f value)
    	echo $server
    	IP="$(cut -d'=' -f2 <<<"$server")"
		openstack loadbalancer member create --name $node --subnet-id $subnet --address $IP --protocol-port 80 $poolName
    fi
done

###### Query free floating ips
float_ip=""
counter=0
while [[ $float_ip == "" ]]
do
	if [[ "$counter" -lt "$limit" ]];then
		floatingIPS=$(openstack floating ip list -c 'Floating IP Address' -f value --status DOWN)
		for ip in $floatingIPS; do
			float_ip=$ip
		done

		###### If not floating IP found create one
		if [[ $float_ip == "" ]]; then
			###### Find an external network to create the floating IP
			networks=$(openstack network list -c Name -f value --external)
			networksName=""
			for network in $networks; do
				networksName=$network
			done

			if [[ $networksName != "" ]];then
				openstack floating ip create $networksName
			fi
		fi
	fi
	((counter=counter+1))
	if [[ "$counter" -gt "$limit" ]];then
		echo "Exiting after retry number $counter, please the openstack environment"
		return
	fi
done
port=$(openstack loadbalancer show -c vip_port_id -f value $loadBalancer)
openstack floating ip set --port $port $float_ip
