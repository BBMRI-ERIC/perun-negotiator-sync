#!/usr/bin/env python3
import json
import sys

import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

SERVICE_NAME = "bbmri_negotiator"
CONFIG_PATH = f"/etc/perun/services/{SERVICE_NAME}"  # folder containing the configuration file
CONFIG_PROPS = ["client_id", "client_secret", "resource", "token_url", "api_url"]

# Global variables
access_token = None
client_id = "123"
client_secret = "123"
resource = ""
token_url = "http://localhost:4011/connect/token"
api_url = "http://localhost:8081/api/v3"
resources_mapping = {}  # {external (Perun) ID: internal (Negotiator) ID}
resources_unknown = set()
updated_resources = 0
session = None


def renew_access_token():
    """Gets new access token from token endpoint"""
    payload = {"grant_type": "client_credentials", "resource": resource}

    response = session.post(token_url, auth=(client_id, client_secret), data=payload)
    if not response.ok:
        print(f"Could not obtain access token: {response.content}")
    global access_token
    access_token = response.json().get("access_token")


def load_config_variables():
    """
    Loads global variables from /etc/perun/services/bbmri_negotiator/bbmri_negotiator.py
    """
    global client_id, client_secret, resource, token_url, api_url
    try:
        sys.path.insert(1, CONFIG_PATH)
        credentials = __import__("bbmri_negotiator")
        client_id = credentials.client_id
        client_secret = credentials.client_secret
        resource = credentials.resource
        token_url = credentials.token_url
        api_url = credentials.api_url
    except Exception as e:
        print(
            f"Could not load configuration. Expected {CONFIG_PROPS} fields in {CONFIG_PATH}/{SERVICE_NAME}.py\n{e}"
        )
        exit(1)


def parse_input(filepath):
    """
    Loads users input file.
    :param filepath: Path to the input file
    :return: Json structure
    """
    with open(filepath, "rb") as f:
        return json.load(f)


def fetch_users():
    """
    Fetches all users from api
    :return: Fetched users
    """
    endpoint_url = api_url + "/users"
    #endpoint_url = api_url + "/requests"

    users = []
    response = session.get(endpoint_url)
    if not response.ok:
        print(f"Unable to fetch users: {response.content}")
        exit(1)
    response = response.json()
    users.extend(response.get("_embedded", {}).get("users", []))
    page = 0
    while response.get("page", {}).get("totalPages", 0) > page:
        response = session.get(endpoint_url + "?page=" + str(page))
        if not response.ok:
            if not response.ok:
                print(f"Unable to fetch users: {response.content}")
                exit(1)
        response = response.json()
        page = response.get("page").get("number") + 1
        users.extend(response.get("_embedded", {}).get("users", []))
    return users


def fetch_resources(user_id=None, resource_endpoint="resources", mapping_id_name = "sourceId"):
    """
    Fetches all resources from api
    :param user_id: Id of user to fetch resources for (optional)
    :param resource_endpoint: Endpoint to fetch resources from
    :return: Fetched resources
    """
    user_part = f"/users/{user_id}" if user_id else ""
    endpoint_url = f"{api_url}{user_part}/{resource_endpoint}"
    resources = []
    response = session.get(endpoint_url)
    if not response.ok:
        if not response.ok:
            print(f"Unable to fetch resources: {response.content}")
            exit(1)
    response = response.json()
    resources.extend(response.get("_embedded", {}).get("resources", []))
    page = 0

    while response.get("page", {}).get("totalPages", 0) > page:
        response = session.get(endpoint_url + "?page=" + str(page))
        if not response.ok:
            if not response.ok:
                print(f"Unable to fetch resources: {response.content}")
                exit(1)
        response = response.json()
        page = response.get("page").get("number") + 1
        resources.extend(response.get("_embedded", {}).get(resource_endpoint, []))

    # save the mapping for later
    for their_resource in resources:
        resources_mapping[their_resource[mapping_id_name]] = their_resource["id"]

    return resources

def add_resource(user_id, resource_id, resource_endpoint="resources"):
    """
    Adds a resource to the user
    :param user_id:
    :param resource_id:
    :param resource_endpoint:
    :return:
    """
    endpoint_url = f"{api_url}/users/{user_id}/{resource_endpoint}"
    data = {"id": resource_id}
    response = session.patch(
        endpoint_url,
        json=data,
        headers={"Authorization": "Bearer " + access_token},
    )
    if not response.ok:
        if not response.ok:
            print(f"Unable to add resource: {response.content}")
            exit(1)


def remove_resource(user_id, resource_id, resource_endpoint="resources"):
    """
    Removes a resource from the user
    :param user_id:
    :param resource_id:
    :param resource_endpoint:
    :return:
    """
    endpoint_url = f"{api_url}/users/{user_id}/{resource_endpoint}/{resource_id}"
    response = session.delete(endpoint_url)
    if not response.ok:
        if not response.ok:
            print(f"Unable to remove resource: {response.content}")
            exit(1)


def update_user(our_user, their_user, resource_type="collections"):
    """
    Check user's assigned resources. Add missing ones and remove redundant ones.
    :param our_user: User entry from generated data
    :param their_user: Fetched user
    :param resource_type: Type of resource to check
    :return:
    """
    mapping_id_name = "sourceId"
    sections = ["membership"]
    if resource_type == "collections":
        resource_endpoint = "resources"
        sections = ["membership"]
    elif resource_type == "networks":
        resource_endpoint = resource_type
        mapping_id_name = "externalId"
        sections = ["membership","administrator"]

    else:
        resource_endpoint = resource_type
    their_resources = fetch_resources(their_user["id"], resource_endpoint, mapping_id_name)
    our_resources = []
    for section in sections:
        our_resources.extend(our_user[section][resource_type])
    #our_resources.extend(our_user["membership"][resource_type])
    # our_resources.extend(our_user["membership"]["biobanks"])
    # our_resources.extend(our_user["membership"]["collections"])
    # our_resources.extend(our_user["membership"]["national_nodes"])
    # our_resources.extend(our_user["membership"]["networks"])

    updated = False
    for our_resource in our_resources:
        their_resource = next(
            filter(lambda r: r[mapping_id_name] == our_resource, their_resources), None
        )
        if not their_resource:
            their_resource_id = resources_mapping.get(our_resource)
            if not their_resource_id:
                resources_unknown.add(our_resource)
                continue
            add_resource(their_user["id"], their_resource_id, resource_endpoint)
            updated = True

    for their_resource in their_resources:
        our_resource = next(
            filter(lambda r: r == their_resource[mapping_id_name], our_resources), None
        )
        if not our_resource:
            remove_resource(their_user["id"], their_resource["id"], resource_endpoint)
            updated = True

    global updated_resources
    updated_resources += 1 if updated else 0


def print_stats():
    print(f"Updated resources for {updated_resources} users.")
    if resources_unknown:
        print(f"Resources not found in Negotiator: {resources_unknown}")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        filepath = sys.argv[1]
    else:
        print("Filepath was not passed!")
        exit()

    load_config_variables()
    our_users = parse_input(filepath)

    retry_strategy = Retry(
        total=2, status_forcelist=[429, 500, 502, 503, 504], backoff_factor=2
    )  # might want to add automatic access token renewal
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    renew_access_token()
    headers = {"Authorization": "Bearer " + access_token}
    session.headers.update(headers)

    their_users = fetch_users()
    their_resources = fetch_resources()
    their_networks = fetch_resources(resource_endpoint="networks", mapping_id_name="externalId")

    for our_user in our_users:
        their_user = next(
            (u for u in their_users if u["subjectId"] == our_user["id"]),
            None,
        )

        if their_user:
            update_user(our_user, their_user, "collections")
            update_user(our_user, their_user, "networks")
    print_stats()
