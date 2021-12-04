import time
import boto3

with open('ohio_launch_script.txt','r') as f:
    ohio_user_data = f.read()

resource_ohio = boto3.resource('ec2')
client_ohio = boto3.client('ec2')

ohio_instances = resource_ohio.instances.filter(Filters=[{'Name': 'tag:Name', 'Values': ['InstanciaSamuel']}])
ohio_instances.terminate()

ohio_instance = resource_ohio.create_instances(
    ImageId='ami-020db2c14939a8efb',
    InstanceType='t2.micro',
    KeyName='SamuelOhio',
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[
        'sg-08e9762e9552e262b'
    ],
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'InstanciaSamuel'
                },
            ]
        }
    ],
    UserData=ohio_user_data
)

ohio_instance[0].wait_until_running(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'InstanciaSamuel',
            ]
        },
    ],
)

print("ohio instance created\n")

ohio_properties = client_ohio.describe_instances(Filters=[{'Name': 'instance-id', 'Values': [ohio_instance[0].id]}])

ohio_ip = ohio_properties['Reservations'][0]['Instances'][0]['PublicIpAddress']

with open('virginia_launch_script.txt', 'r') as f:
    data = f.readlines()

data[10] = f"""sudo sed -i "s/'HOST': 'POSTGRES_IP'/'HOST': '{ohio_ip}'/g" ./portfolio/settings.py\n"""

with open('virginia_launch_script.txt', 'w') as f:
    f.writelines(data)

with open('virginia_launch_script.txt','r') as f:
    virginia_user_data = f.read()

resource_virginia = boto3.resource('ec2', region_name='us-east-1')
client_virginia = boto3.client('ec2', region_name='us-east-1')
elbv2_virginia = boto3.client('elbv2', region_name='us-east-1')
autoscaling_virginia = boto3.client('autoscaling', region_name='us-east-1')

autoscaling_virginia.delete_auto_scaling_group(
                    AutoScalingGroupName='auto-scaling-samuel',
                    ForceDelete=True
                )

time.sleep(60)

autoscaling_virginia.delete_launch_configuration(LaunchConfigurationName='launch-config-samuel')

time.sleep(60)

load_balancers = elbv2_virginia.describe_load_balancers(Names=['load-balancer-samuel'])
elbv2_virginia.delete_load_balancer(LoadBalancerArn=load_balancers['LoadBalancers'][0]['LoadBalancerArn'])

time.sleep(60)

target_groups = elbv2_virginia.describe_target_groups()["TargetGroups"]
elbv2_virginia.delete_target_group(TargetGroupArn=target_groups[0]["TargetGroupArn"])

time.sleep(60)

imgs = client_virginia.describe_images(Owners=['self'])
client_virginia.deregister_image(ImageId=imgs['Images'][0]['ImageId'])

virginia_instance = resource_virginia.create_instances(
    ImageId='ami-0279c3b3186e54acd',
    InstanceType='t2.micro',
    KeyName='Samuel',
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[
        'sg-2e631864'
    ],
    TagSpecifications=[
        {
            'ResourceType': 'instance',
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': 'InstanciaSamuel'
                },
            ]
        }
    ],
    UserData=virginia_user_data
)

virginia_instance[0].wait_until_running(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'InstanciaSamuel',
            ]
        },
    ],
)

time.sleep(180)

print("virginia instance created\n")

virginia_image = virginia_instance[0].create_image(Name='VirginiaImage')

virginia_image.wait_until_exists()

state = virginia_image.state

while state != 'available':
    time.sleep(90)

    img = resource_virginia.Image(virginia_image.id)

    state = img.state

print("virginia image created\n")

virginia_instance[0].terminate()

virginia_instance[0].wait_until_terminated(
    Filters=[
        {
            'Name': 'tag:Name',
            'Values': [
                'InstanciaSamuel',
            ]
        },
    ],
)

print("virginia instance terminated\n")

target_group = elbv2_virginia.create_target_group(
    Name='target-samuel',
    Port=8080,
    Protocol='HTTP',
    HealthCheckProtocol='HTTP',
    TargetType='instance',
    VpcId=client_virginia.describe_vpcs()["Vpcs"][0]["VpcId"],
    Matcher={'HttpCode': '200,301,302,403,404'},
    HealthCheckPath='/admin',
    HealthCheckPort='8080',
    HealthCheckEnabled=True,
)

print("virginia target group created\n")

load_balancer = elbv2_virginia.create_load_balancer(
    Name='load-balancer-samuel',
    SecurityGroups=['sg-2e631864'],
    Scheme='internet-facing',
    Subnets=[subnet['SubnetId'] for subnet in client_virginia.describe_subnets()['Subnets']],
    Type = 'application',
    IpAddressType = 'ipv4',
)

time.sleep(180)

with open('load_balancer_dns.txt', 'r') as f:
    data = f.readlines()

data[0] = load_balancer['LoadBalancers'][0]['DNSName'] 

with open('load_balancer_dns.txt', 'w') as f:
    f.writelines(data)

print("virginia load balancer created\n")

listener = elbv2_virginia.create_listener(
    DefaultActions=[
        {
            'TargetGroupArn': target_group['TargetGroups'][0]['TargetGroupArn'],
            'Type': 'forward',
        },
    ],
    LoadBalancerArn=load_balancer['LoadBalancers'][0]['LoadBalancerArn'],
    Port=80,
    Protocol='HTTP',
)

print("virginia listener created\n")

launch_configuration = autoscaling_virginia.create_launch_configuration(
    ImageId=virginia_image.id,
    InstanceType='t2.micro',
    KeyName='Samuel',
    LaunchConfigurationName='launch-config-samuel',
    SecurityGroups=[
        'sg-2e631864',
    ],
)

print("virginia launch configuration created\n")

autoscaling = autoscaling_virginia.create_auto_scaling_group(
    AutoScalingGroupName='auto-scaling-samuel',
    HealthCheckGracePeriod=300,
    HealthCheckType='ELB',
    MaxSize=3,
    MinSize=1,
    TargetGroupARNs=[target_group['TargetGroups'][0]['TargetGroupArn']],
    AvailabilityZones=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'us-east-1e', 'us-east-1f'],
    LaunchConfigurationName='launch-config-samuel',
)

time.sleep(180) 

print("virginia autoscaling created\n")