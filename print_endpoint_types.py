import requests
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    token_type: str

def get_token(url:str, username:str, password:str):
    response:dict = requests.post(url, {"username": username, "password": password}).json()
    return Token(access_token=response['access_token'], token_type=response['token_type'])

def get_endpoint_types(url:str, token:Token, nonetype_override: str or None = any) -> None or dict:
    headers = {'Authorization': 'Bearer ' + token.access_token}
    response = requests.get(url, headers=headers)
    data = response.json()[0]
    print(data)
    types = []
    manual_types = []
    for key, value in data.items():
        value_type = type(value)
        if value_type is dict: 
            types.append(f'{key}: dict\n')
        elif value_type is list:
            types.append(f'{key}: list\n')
        elif value_type is str:
            types.append(f'{key}: str\n')
        elif value_type is int:
            types.append(f'{key}: int\n')
        elif value_type is float:
            types.append(f'{key}: float\n')
        elif value_type is bool:
            types.append(f'{key}: bool\n')
        elif value_type == type(None):
             types.append(f'{key}: {nonetype_override}\n')
            # else:
            #     types.append(f'{key}: **NONE TYPE DECTECTED**\n')
            #     manual_types.append(key)
        else:
            types.append(f'{key}: {value_type}')
            

    with open('types.txt', 'w') as f:
        f.writelines(types)
    if len(manual_types) > 0:
        with open('manual_types.txt', 'w') as f:
            f.writelines(f"""'{"','".join(manual_types)}'""")

    return (data,types)



def main():
    base_url = 'http://localhost:8000'
    token = get_token(f'{base_url}/token/', 'app1','Money2020!')
    print(token)
    types = get_endpoint_types(f'{base_url}/schools/6', token, nonetype_override='int')
    print(types[0])




if __name__ == '__main__':
    main()