#!/bin/bash
###### sourcing the rc file to prevent any errors
. CloudComp12-openrc.sh

######## Define variable 
loadBalancer="loadBalancer1"
loadBalancerStatus="NOTACTIVE"
poolName="pool1"
listenerName="listener1"
monitorName="health-Monitor"


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
###### Take only one member
members=$(openstack loadbalancer member list -c name -f value $poolName)
memberToRemove=""
memberToRemoveName=""
memberToRemoveIP=""
for instances in $members; do
	servers=$(openstack server list -c ID -c Name -c Networks -f value --name $instances)
	for server in $servers; do
		if [[ "$memberToRemove" != "" ]]; then
			if [[ "$memberToRemoveName" != "" ]]; then
				if [[ "$memberToRemoveIP" == "" ]]; then
					memberToRemoveIP="$(cut -d'=' -f2 <<<"$server")"
				fi
			fi
		fi

		if [[ "$memberToRemove" != "" ]]; then
			if [[ "$memberToRemoveName" == "" ]]; then
				memberToRemoveName="$server"
			fi
		fi

		if [[ "$memberToRemove" == "" ]]; then
			memberToRemove="$server"
		fi
	done
done

# ##### Remove member from the pool
members=$(openstack loadbalancer member list -c id -c address -f value $poolName)
lastID=""
for instances in $members; do
	if [[ "$instances" == "$memberToRemoveIP" ]]; then
		openstack loadbalancer member delete  --wait $poolName $lastID
		echo "$instances removal from pool completed successfully"
	fi
	lastID=$instances
done

##### Remove instance 
openstack server delete $memberToRemove

echo "Scale in completed successfully"
echo "See the list of instances running"
servers=$(openstack server list -c Name -f value)
for server in $servers; do
	echo "Server :: $server"
done