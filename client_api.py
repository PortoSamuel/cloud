import datetime
import requests
from requests.auth import HTTPBasicAuth

with open('load_balancer_dns.txt', 'r') as f:
    data = f.readlines()

dns = data[0]

result = requests.get(f'http://{dns}/tasks/', auth=HTTPBasicAuth('cloud','cloud'))

print(result.content)

dt = {
    'title' : 'Tasks Teste',
    'pub_date' : datetime.datetime.now(),
    'description' : 'Descrição',
}

result = requests.post(f'http://{dns}/tasks/', data=dt,  auth=HTTPBasicAuth('cloud','cloud'))

print(result)

