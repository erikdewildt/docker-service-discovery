# Docker Service Discovery

This projects provides a distributed, reliable key-value store setup used for service-discovery within a docker 
swarm environment.

## Introduction

In a docker swarm environment there is no way to control the startup order of nodes withing the swarm. As some 
services need to be deployed redundant in a master/slave setup a mechanism is needed to control the lifecycle
of services within the swarm.

My [docker-cluster-controller] project provides a python class to manage this service lifecycle from within a 
`docker-entrypoint` script.

However a central key-value store is required to store an instances properties like its role in a cluster. This project
provides the Dockerfile to create a [etcd] image and a compose file which can be used to start a [etcd] cluster.

## ETCD Image

The image can be build using `docker build -t etcd .` and needs  some environment variable's set to operate:

|Variable |Description |
|---------|------------|
|ETCD_UUID |A UUID for the cluster (in a bash shell use `uuidgen` to generate a UUID)|
|ETCD_CLUSTER_SIZE |The number of nodes in the cluster, a cluster should have a minimum of 2 nodes.|
|ETCD_DISCOVERY_NODE |The discovery node |

To start a cluster a so called `bootstrap` node is needed. This node is only required during the startup of the cluster.

## ETCD Swarm Setup

The swarm has two networks: sd_backend and sd_frontend. The backend network is used for communication between the
ETCD nodes and the bootstrap node. The frontend network can be used to have other containers connect to the ETCD cluster.


### Usage

```bash
docker build -t etcd .
docker stack deploy -c docker-swarm.yml etcd-cluster
```

Check the cluster: 
```bash
docker stack ps etcd-cluster
```

Check the logs: 
```bash
docker service logs etcd-cluster_bootstrap-service-discovery
docker service logs etcd-cluster_service-discovery
```
           

[docker-cluster-controller]: https://github.com/erikdewildt/docker-cluster-controller
[etcd]: https://etcd.readthedocs.io/en/latest/faq.html#what-is-etcd
