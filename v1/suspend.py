import requests
import json
import warnings

# Suppress only the InsecureRequestWarning
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

def suspend_server_by_name(server_name, api_url):
    # Define the payload and headers
    payload = {'name': server_name}
    headers = {'Content-Type': 'application/json'}

    try:
        # Make the POST request, bypassing SSL verification
        response = requests.post(api_url, data=json.dumps(payload), headers=headers, verify=False)
        
        # Check the response status
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    print('Server suspended successfully')
                else:
                    print(f"Error suspending server: {data.get('error')}")
            except json.JSONDecodeError:
                print("Failed to decode JSON response. Response content:")
                print(response.text)
        else:
            print(f"Request failed with status code {response.status_code}. Response content:")
            print(response.text)

    except requests.RequestException as e:
        print(f"An error occurred: {e}")


def main():
    # Input the server name and API URL
    server_name = input("Enter the Server Name to suspend: ")
    api_url = 'https://194.120.116.224:5001/api/suspend' 

    # Call the suspend_server_by_name function
    suspend_server_by_name(server_name, api_url)

if __name__ == '__main__':
    main()
