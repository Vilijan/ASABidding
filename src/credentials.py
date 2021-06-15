from algosdk.v2client import algod
import yaml
import os
from pathlib import Path


def load_config():
    path = Path(os.path.dirname(__file__))
    config_location = os.path.join(path.parent, "config.yml")

    with open(config_location) as file:
        return yaml.full_load(file)


def get_client():
    """
    :return:
        Returns algod_client
    """
    config = load_config()

    token = config.get('client_credentials').get('token')
    address = config.get('client_credentials').get('address')
    purestake_token = {'X-Api-key': token}

    algod_client = algod.AlgodClient(token, address, headers=purestake_token)
    return algod_client


def main_developer_credentials() -> (str, str):
    """
    :return:
        private_key: str
        public_key: str
    """
    config = load_config()

    private_key = config.get('main_developer_credentials').get('private_key')
    public_key = config.get('main_developer_credentials').get('public_key')

    return private_key, public_key


def get_developer_credentials(developer_id: int) -> (str, str):
    """
        :return:
            private_key: str
            public_key: str
        """
    config = load_config()

    private_key = config.get(f'developer_{developer_id}_credentials').get('private_key')
    public_key = config.get(f'developer_{developer_id}_credentials').get('public_key')

    return private_key, public_key
