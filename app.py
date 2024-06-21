from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.containerinstance.models import (
    ContainerGroup,
    Container,
    ContainerGroupNetworkProtocol,
    ContainerPort,
    EnvironmentVariable,
    IpAddress,
    OperatingSystemTypes,
    Port,
    ResourceRequests,
    ResourceRequirements
)
import os

app = Flask(__name__)

# Azure configuration
SUBSCRIPTION_ID = 'your_subscription_id'
RESOURCE_GROUP = 'your_resource_group'
CONTAINER_GROUP_NAME = 'your_container_group_name'
CONTAINER_NAME = 'your_container_name'
IMAGE = 'your_docker_image'

# Azure credentials
credential = DefaultAzureCredential()
client = ContainerInstanceManagementClient(credential, SUBSCRIPTION_ID)

@app.route('/start-container', methods=['POST'])
def start_container():
    # Get input data from the request
    data = request.get_json()
    cpu_cores = data.get('cpu_cores', 1)
    memory_gb = data.get('memory_gb', 1.5)
    environment_variables = data.get('environment_variables', {})

    # Convert environment variables dictionary to a list of EnvironmentVariable objects
    env_vars = [EnvironmentVariable(name=k, value=v) for k, v in environment_variables.items()]

    # Create container resource requirements
    resource_requirements = ResourceRequirements(
        requests=ResourceRequests(
            cpu=cpu_cores,
            memory_in_gb=memory_gb
        )
    )

    # Create container instance
    container = Container(
        name=CONTAINER_NAME,
        image=IMAGE,
        resources=resource_requirements,
        environment_variables=env_vars
    )

    # Create container group
    container_group = ContainerGroup(
        location='your_azure_region',
        containers=[container],
        os_type=OperatingSystemTypes.linux,
        ip_address=IpAddress(
            ports=[Port(protocol=ContainerGroupNetworkProtocol.tcp, port=80)],
            type='Public'
        )
    )

    # Start container group
    client.container_groups.begin_create_or_update(RESOURCE_GROUP, CONTAINER_GROUP_NAME, container_group)

    return jsonify({'message': 'Container started successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True)
