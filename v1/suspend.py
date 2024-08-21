import requests
import json

def suspend_server(server_id, api_url):
    # Define the payload and headers
    payload = {'id': server_id}
    headers = {'Content-Type': 'application/json'}

    try:
        # Make the POST request
        response = requests.post(api_url, data=json.dumps(payload), headers=headers)
        
        # Check the response status
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print('Server suspended successfully')
            else:
                print(f"Error suspending server: {data.get('error')}")
        else:
            print(f"Request failed with status code {response.status_code}")

    except requests.RequestException as e:
        print(f"An error occurred: {e}")

def main():
    # Input the server ID and API URL
    server_id = input("Enter the Server ID to suspend: ")
    api_url = 'https://194.120.116.224:5001/api/suspend' 

    # Call the suspend_server function
    suspend_server(server_id, api_url)

if __name__ == '__main__':
    main()
