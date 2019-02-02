#!/usr/bin/env python3
"""Docker Entrypoint."""
import argparse
import json
import multiprocessing
import os
import socket
import requests
from time import sleep, time

import sys
from clustercontroller.clustercontroller import start_process, monitor_processes, create_logger, terminate_all_processes

# Define command line arguments
parser = argparse.ArgumentParser(description='Docker Entrypoint')
parser.add_argument('-s', '--start', help="Start Cluster", action='store_true', default=False)
parser.add_argument('--standalone', help="Start Stand-Alone", action='store_true', default=False)
parser.add_argument('--bootstrap', help="Start Bootstrap node", action='store_true', default=False)
parser.add_argument('--debug', help="Enable debugging", action='store_true', default=False)
args = parser.parse_args()


if __name__ == '__main__':

    logger = create_logger(name='docker_entrypoint')
    logger.info('Docker Entrypoint started.')
    if args.debug:
        logger.info(f'Environment Variables: \n{json.dumps(dict(os.environ), indent=2)}')

    # Initialise the global processes list used to monitor active processes.
    processes = []
    # Define the multiprocessing terminate event. When this event is set all processes will start to terminate.
    cluster_controller_started_event = multiprocessing.Event()
    terminate_event = multiprocessing.Event()

    hostname = os.uname()[1]
    etcd_discovery_node = os.environ.get('ETCD_DISCOVERY_NODE')
    etcd_uuid = os.environ.get('ETCD_UUID')

    if args.standalone:
        logger.info('Starting in standalone mode.')
        command = ['tail', '-f', '/dev/null']  # ToDo: Standalone command
        # Start the process without a cluster controller
        process = start_process(command, name='etcd', terminate_event=terminate_event)
        processes.append((process, process.name))

    elif args.bootstrap:
        command = ["/usr/bin/etcd", "--name", "bootstrap",
                   "--data-dir", "/data",
                   "--advertise-client-urls", f"http://{hostname}:4001",
                   "--listen-client-urls", "http://0.0.0.0:4001",
                   "--initial-advertise-peer-urls", f"http://{hostname}:2380",
                   "--listen-peer-urls", "http://0.0.0.0:2380",
                   "--initial-cluster-token", "etcd-cluster-1",
                   "--initial-cluster", f"bootstrap=http://{hostname}:2380",
                   "--initial-cluster-state", "new"]
        logger.info('Starting Bootstrap node.')
        process = start_process(command, name='etcd', terminate_event=terminate_event)
        processes.append((process, process.name))

        etcd_active = False
        timeout = time() + 30
        while not etcd_active and time() < timeout:
            sleep(1)
            try:
                socket.create_connection(address=('127.0.0.1', int(4001)), timeout=5)
                etcd_active = True
            except socket.error as error:
                logger.info(f'Checking if ETCD is active, connection to port 4001 failed: {error}')
                etcd_active = False

        if etcd_active:
            logger.info('ETCD is active')
            data = {'value': os.environ.get('ETCD_CLUSTER_SIZE')}
            response = requests.put(f"http://{hostname}:4001/v2/keys/discovery/{etcd_uuid}/_config/size", data=data,
                                    stream=False)
            logger.info(f'Initialised Bootstrap node, reponse code: {response.status_code}')
        else:
            logger.info('ETCD not active within timeout, exiting...')
            terminate_all_processes(processes=processes, terminate_event=terminate_event, logger=logger)
            sys.exit(0)

    elif args.start:
        command = ["/usr/bin/etcd", "-name", f"{hostname}", "--data-dir", "/data",
                   "--initial-advertise-peer-urls", f"http://{hostname}:2380",
                   "--listen-peer-urls", "http://0.0.0.0:2380",
                   "--listen-client-urls", "http://0.0.0.0:2379,http://0.0.0.0:4001",
                   "--advertise-client-urls", f"http://{hostname}:2379",
                   "--discovery", f"http://{etcd_discovery_node}:4001/v2/keys/discovery/{etcd_uuid}"]
        logger.info('Starting in cluster mode.')

        # Wait until bootstrap node is active
        etcd_bootstrap_active = False
        timeout = time() + 30
        while not etcd_bootstrap_active and time() < timeout:
            sleep(1)
            try:
                socket.create_connection(address=(f'{etcd_discovery_node}', int(4001)), timeout=5)
                logger.info('Successfully connected to ETCD bootstrap node on port 4001')
                etcd_bootstrap_active = True
                sleep(10)  # Wait 10 seconds to have the bootstrap node fully initialised
            except socket.error as error:
                logger.info(f'Checking if ETCD bootstrap is active, connection to port 4001 failed: {error}')
                etcd_bootstrap_active = False

        if not etcd_bootstrap_active:
            logger.info('ETCD bootstrap node not active within timeout, exiting...')
            terminate_all_processes(processes=processes, terminate_event=terminate_event, logger=logger)
            sys.exit(0)

        # Start ETCD
        process = start_process(command, name='etcd', terminate_event=terminate_event)
        processes.append((process, process.name))

        # Validate correct startup of ETCD
        etcd_active = False
        timeout = time() + 30
        while not etcd_active and time() < timeout:
            try:
                socket.create_connection(address=('127.0.0.1', int(2379)), timeout=5)
                logger.info(f'Successfully connected to ETCD on port 2379')
                etcd_active = True
            except socket.error as error:
                logger.info(f'Checking if ETCD is active, connection to port 2379 failed: {error}')
                etcd_active = False

        if not etcd_active:
            logger.info('ETCD not active within timeout, exiting...')
            terminate_all_processes(processes=processes, terminate_event=terminate_event, logger=logger)
            sys.exit(0)

    # Monitor processes, this will cause the container to stay active until one of the processes stops.
    monitor_processes(processes=processes, terminate_event=terminate_event)
    logger.info('Docker Entrypoint exited.')
