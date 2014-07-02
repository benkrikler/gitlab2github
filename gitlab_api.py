""" Thin wrapper to the Gitlab API (http://api.gitlab.org/) """

import json
import requests
import config

def request(path, method='GET', params=None, debug=False):
    """
    Make a request to the Gitlab API.

    :param path: The path to the call being made
    :type path: str

    :param method: The HTTP method (GET, POST, PUT, DELETE, PATCH)
    :type method: str

    :param params: Dictionary of parameters to be passed on the call
    :type params: dict
    """
    url = '{}/api/v3{}?private_token={}&per_page={}'.format(
        config.gitlab_url, path, config.gitlab_api_token, 1000)
    if debug: print("[REQUEST] " + url)
    return requests.request(method, url, data=json.dumps(params), verify=False).json()
