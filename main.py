import os
import subprocess
import hvac  # For HashiCorp Vault
import boto3  # For AWS Parameter Store
import gnupg  # For GPG encryption
import yaml

# Configurations
VAULT_URL = 'https://your-vault-url'
VAULT_TOKEN = 'your-vault-token'
SECRET_PATH = 'secret/data/client_credentials'

# AWS Parameter Store config
AWS_REGION = 'us-west-2'
PARAMETER_NAME_CLIENT_ID = '/yourapp/clientId'
PARAMETER_NAME_CLIENT_SECRET = '/yourapp/clientSecret'

GPG_RECIPIENT = 'saltmaster@example.com'
PILLAR_FILE_PATH = '/srv/pillar/client_credentials.sls'
GIT_REPO_PATH = '/srv/pillar/'

def fetch_secrets_from_vault():
    """Fetch secrets from HashiCorp Vault."""
    client = hvac.Client(url=VAULT_URL, token=VAULT_TOKEN)
    secret_response = client.secrets.kv.v2.read_secret_version(path=SECRET_PATH)
    
    client_id = secret_response['data']['data']['clientId']
    client_secret = secret_response['data']['data']['clientSecret']
    
    return client_id, client_secret

def fetch_secrets_from_aws_parameter_store():
    """Fetch secrets from AWS Systems Manager Parameter Store."""
    ssm = boto3.client('ssm', region_name=AWS_REGION)
    
    client_id = ssm.get_parameter(Name=PARAMETER_NAME_CLIENT_ID, WithDecryption=True)['Parameter']['Value']
    client_secret = ssm.get_parameter(Name=PARAMETER_NAME_CLIENT_SECRET, WithDecryption=True)['Parameter']['Value']
    
    return client_id, client_secret

def encrypt_with_gpg(data):
    """Encrypt data using GPG."""
    gpg = gnupg.GPG()
    
    encrypted_data = gpg.encrypt(data, GPG_RECIPIENT)
    if not encrypted_data.ok:
        raise Exception("GPG encryption failed: " + encrypted_data.status)
    
    return str(encrypted_data)

def update_salt_pillar(client_id, client_secret):
    """Update Salt pillar with the encrypted credentials."""
    encrypted_client_id = encrypt_with_gpg(client_id)
    encrypted_client_secret = encrypt_with_gpg(client_secret)
    
    pillar_data = {
        'client_credentials': {
            'clientId': encrypted_client_id,
            'clientSecret': encrypted_client_secret
        }
    }
    
    with open(PILLAR_FILE_PATH, 'w') as pillar_file:
        yaml.dump(pillar_data, pillar_file)
    
    # Commit to git
    commit_salt_pillar()

def commit_salt_pillar():
    """Commit the updated Salt pillar to git."""
    os.chdir(GIT_REPO_PATH)
    
    subprocess.run(['git', 'add', PILLAR_FILE_PATH], check=True)
    subprocess.run(['git', 'commit', '-m', 'Update client credentials in pillar'], check=True)
    subprocess.run(['git', 'push'], check=True)

def main():
    # Uncomment the correct secret fetching method:
    
    # Fetch secrets from Vault
    # client_id, client_secret = fetch_secrets_from_vault()

    # Fetch secrets from AWS Parameter Store
    client_id, client_secret = fetch_secrets_from_aws_parameter_store()

    # Update the Salt pillar with encrypted credentials
    update_salt_pillar(client_id, client_secret)
    
    print("Successfully updated Salt pillar and committed to git.")

if __name__ == '__main__':
    main()

