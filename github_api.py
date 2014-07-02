""" Thin wrapper to the Github API (http://developer.github.com/v3/) """

import json
import requests
import config

def request(path, method='GET', params=None, debug=False):
    """
    Make a request to the Github API.
    
    :param path: the path to the call being made
    :type path: str

    :param method: the HTTP method (GET, POST, PUT, DELETE, PATCH)
    :type method: str

    :param params: parameters to be passed on the request
    :type params: dict
    """
    url = 'https://{}:{}@api.github.com{}'.format(
        config.github_user, config.github_api_token, path)
    if debug: print("[REQUEST] " + url)
    return requests.request(method, url, data=json.dumps(params)).json()