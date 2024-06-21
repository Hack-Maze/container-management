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
    EnvironmentVariable,
    IpAddress,
    OperatingSystemTypes,
    ResourceRequests,
    ResourceRequirements
)
import docker


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
    # Handle the exception here, you can print an error message or raise a custom exception
    raise Exception('Failed to authenticate with Azure. Please check your credentials and try again.')



# Initialize the client
client = ContainerInstanceManagementClient(credential, SUBSCRIPTION_ID)







def check_if_image_exists(image_name):
    try:
        client = docker.from_env()
        client.images.pull(image_name)
        return True
    except Exception as e:
        return False


@app.route('/start-container', methods=['POST'])
def start_container():
    # Get input data from the request
    data                  = request.get_json()
    maze_title            = data.get('maze_title')
    user_name             = data.get('user_name')
    container_image       = data.get('container_image')
    environment_variables = data.get('environment_variables', {})
    open_ports            = data.get('open_ports', [])
    container_group_name  = f"{maze_title.lower()}-{user_name}-container-group"
    resource_group_name   = f"{maze_title.lower()}-{user_name}-rg"
    container_name        = f"{maze_title.lower()}-{user_name}-container"
    # Check if the container image exists

    if  not check_if_image_exists(container_image):
        return jsonify({'message': 'Container image does not exist'}), 400
    
    # Check if all required data is provided
    if not maze_title or not user_name or not container_image  or open_ports == [] or environment_variables == {}:
        return jsonify({'message': 'Bad Request: Missing required data'}), 400

    region                =  "italynorth"
    DNS_name              = f"{maze_title.lower()}-{user_name}"
    cpu_cores             =  1
    memory_gb             =  1.5
    # Convert environment variables dictionary to a list of EnvironmentVariable objects
    env_vars = [EnvironmentVariable(name=k, value=v) for k, v in environment_variables.items()]
    # Convert ports  list to a list of ContainerPort objects    
    ports = [ContainerPort(port=p) for p in open_ports]



    # Create resource group
    resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)

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
            cpu=cpu_cores,
            memory_in_gb=memory_gb
        )
    )

    # Create container instance
    container = Container(
        name                  = container_name,
        image                 = container_image,
        resources             = resource_requirements,
        ports                 = ports,
        environment_variables = env_vars

    )


    # Create container group

    group_ip_address = IpAddress(
        ports         = ports,
        dns_name_label= DNS_name,
        type          ="Public"
        )

    container_group = ContainerGroup(
        location=region,
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
                'DNS': f"{DNS_name}.{region}.azurecontainer.io",
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

@app.route('/stop-container', methods=['POST'])
def stop_container():
    data                  = request.get_json()
    resource_group_name   = data.get('resource_group_name')

    # Check if resource group name is provided
    if not resource_group_name:
        return jsonify({'message': 'Bad Request: Missing resource group name'}), 400

    resource_client = ResourceManagementClient(credential, SUBSCRIPTION_ID)
    # Delete resource group
    try:
        delete_procces = resource_client.resource_groups.begin_delete(resource_group_name)
        delete_procces.wait()
        return jsonify(
        {
            'message': 'Resource group has been deleted successfully',
        }), 200
    except Exception as e:
        return jsonify({'message': 'Resource group could not be found'}), 400




if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=80)
