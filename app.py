from flask import Flask, request, jsonify
import os
from azure.mgmt.resource import  ResourceManagementClient
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.resource.resources.models import ResourceGroup

from azure.mgmt.containerinstance.models import (
    ContainerGroup,
    Container,
    ContainerPort,
    Port,
    EnvironmentVariable,
    IpAddress,
    OperatingSystemTypes,
    ResourceRequests,
    ResourceRequirements
)
from docker import from_env


app = Flask(__name__)

# Azure configuration
# Azure CREDS
load_dotenv()

SUBSCRIPTION_ID = os.getenv('AZURE_SUBSCRIPTION_ID')
TENANT_ID       = os.getenv('AZURE_TENANT_ID')
CLIENT_ID       = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET   = os.getenv('AZURE_CLIENT_SECRET')

# Manually create the credential object using the environment variables

try:
    credential = ClientSecretCredential(tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
except Exception as e:
    raise Exception('Failed to authenticate with Azure. Please check your credentials and try again.')



# Initialize the client
client = ContainerInstanceManagementClient(credential, SUBSCRIPTION_ID)

resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)



# def check_if_image_exists(image_name):
#     try:
#         client = from_env()
#         client.images.pull(image_name)
#         return "ok"
#     except Exception as e:
#         print(e)
#         return e

# add required parameters to the request
@app.route('/start-container', methods=['POST'])
def start_container():
    # Get input data from the request
    data                  = request.get_json()
    maze_title            = data.get('maze_title')
    user_name             = data.get('user_name')
    container_image       = data.get('container_image')
    environment_variables = data.get('environment_variables', {})
    open_ports            = data.get('open_ports', [])


    # print(check_if_image_exists(container_image))
    # if   check_if_image_exists(container_image):
    #     pass
    # else:
    #     return jsonify({'message': 'Container image does not exist'}), 400
    
    # Check if all required data is provided
    if not maze_title or not user_name or not container_image  or open_ports == [] or environment_variables == {}:
        return jsonify({'message': 'Bad Request: Missing required data'}), 400

    container_group_name  = f"{maze_title.lower()}-{user_name}-container-group"
    resource_group_name   = f"{maze_title.lower()}-{user_name}-rg"
    container_name        = f"{maze_title.lower()}-{user_name}-container"

    # Check if the container image exists
    REGION                =  "italynorth"
    DNS_name              = f"{maze_title.lower()}-{user_name}"
    CPU_CORES             =  1
    MEMORY             =  1.5
    # Convert environment variables dictionary to a list of EnvironmentVariable objects
    env_vars = [EnvironmentVariable(name=k, value=v) for k, v in environment_variables.items()]
    # Convert ports  list to a list of ContainerPort objects    
    ports = [ContainerPort(port=p) for p in open_ports]



    # Check if resource group already exists
    if resource_client.resource_groups.check_existence(resource_group_name):
        return jsonify({'message': 'Container already exists'}), 400 
    else:
    
    # Create resource group
        resource_group = ResourceGroup(location="Italy North")
        resource_client.resource_groups.create_or_update(resource_group_name, resource_group)



    # Create container resource requirements
    resource_requirements = ResourceRequirements(
        requests=ResourceRequests(
            cpu=CPU_CORES,
            memory_in_gb=MEMORY
        )
    )

    # Create container instance
    container = Container(
        name                  = container_name,
        image                 = container_image,
        resources             = resource_requirements,
        ports                 = [ContainerPort(port=p) for p in open_ports],
        environment_variables = env_vars

    )


    # Create container group

    group_ip_address = IpAddress(
        ports         = [Port(port=p) for p in open_ports],
        dns_name_label= DNS_name,
        type          ="Public"
        )

    container_group = ContainerGroup(
        location=REGION,
        containers=[container],
        os_type=OperatingSystemTypes.linux,
        ip_address=group_ip_address
    )


    
        
    try:
    # Start container group
        create_process = client.container_groups.begin_create_or_update(resource_group_name, container_group_name, container_group)
        create_process.wait()



        return jsonify(
            {
                'message': 'Container started successfully',
                'DNS': f"{DNS_name}.{REGION}.azurecontainer.io",
                'resource_group_name': f"{resource_group_name}"
            }), 200

    except Exception as e:
        # Delete resource group
        delete_process = resource_client.resource_groups.begin_delete(resource_group_name)
        delete_process.wait()        
        return jsonify({'message': 'resource group could not be created'}), 500


@app.route('/status', methods=['GET'])
def get_status():
        return jsonify(
        {
            'status': 'UP'
        }), 200


def __delete_resource_group(resource_group_name: str):
    try:
        delete_procces = resource_client.resource_groups.begin_delete(resource_group_name)
        delete_procces.wait()
        return jsonify(
            {
                'message': 'Resource group has been deleted successfully',
            }), 200
    except Exception as e:
        return jsonify({'message': 'Resource group could not be found'}), 400


@app.route('/stop-container', methods=['POST'])
def stop_container():
    data                  = request.get_json()
    resource_group_name   = data.get('resource_group_name')

    # Check if resource group name is provided
    if not resource_group_name:
        return jsonify({'message': 'Bad Request: Missing resource group name'}), 400
    return __delete_resource_group(resource_group_name)


@app.route('/stop-all-containers', methods=['POST', 'GET'])
def stop_containers():
    stopped_containers = []
    # get all container groups
    container_groups = client.container_groups.list()

    for container_group in container_groups:
        prefix = container_group.name.split('-')[:-2]
        prefix.append('rg')
        resource_group_name = "-".join(prefix)
        __delete_resource_group(resource_group_name)
        stopped_containers.append(resource_group_name)
    else:
        if stopped_containers:
            return jsonify({'message': f'Stopped all the containers', 'resource_groups': stopped_containers}), 200
        else:
            return jsonify({'message': 'No running containers found'}), 404



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
