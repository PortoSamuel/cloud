import requests
from requests.auth import HTTPBasicAuth

with open('load_balancer_dns.txt', 'r') as f:
    data = f.readlines()

dns = data[0]

result = requests.get(f'http://{dns}/users/', auth=HTTPBasicAuth('cloud','cloud'))

print(result.json())

dt = {
    'username' : 'usuario_teste',
    'email' : 'usuario_teste@testando.com',
}

result = requests.post(f'http://{dns}/users/', data=dt,  auth=HTTPBasicAuth('cloud','cloud'))

print(result.json())