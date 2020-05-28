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

###### Finding a subnet to use
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

###### Getting the name of the current pool 
poolName=$(openstack loadbalancer pool list -c name -f value --loadbalancer loadBalancer1)
###### Getting the members of the pool
members=$(openstack loadbalancer member list -c name -f value $poolName)
memberList=()
for instances in $members; do
	memberList+=( $instances )
done

##### Checking the instances and adding the one not in there (new one)
active_instances=$(openstack server list -c Name -f value --status ACTIVE)
for instances in $active_instances; do
	if [[ $instances == *"app-api"* ]]; then
		if [[ "${memberList[*]}" != *"$instances"* ]]; then
		  	server=$(openstack server list -c Networks --name $instances -f value )
		  	for server_instances in $server; do
			  	IP="$(cut -d'=' -f2 <<<"$server_instances")"
		    	echo "Adding $instances to the pool $IP"
		    	openstack loadbalancer member create --name $instances --subnet-id $subnet --address $IP --protocol-port 80 $poolName
		    done
		fi
	fi
done

echo "Scale out completed successfully"
echo "See the list of members in the current pool"
members=$(openstack loadbalancer member list -c name -f value $poolName)
memberList=()
for instances in $members; do
	echo "Server :: $instances"
done