import os, sys
import requests
import json

# Disable SSL verification and warnings
import urllib3

urllib3.disable_warnings()
verify_ssl = False


def scale_initialized(scale_url):
    ### Check if scale is initialized
    url = scale_url + "/initscale"

    try:
        response = requests.request('PUT', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return None

    if response.status_code == 200:
        return True
    elif response.status_code == 400:
        return False
    elif response.status_code == 500:
        return None
    else:
        # This means something went wrong.
        raise Exception('PUT /initscale/ {}'.format(response.status_code))


def child_on_scale(scale_url):
    ### Check if scale is initialized
    url = scale_url + "/ontop"

    try:
        response = requests.request('GET', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return False

    # print('step on', response.status_code)

    if response.status_code == 200:
        return True
    elif response.status_code == 500 or response.status_code == 400:
        return False
    else:
        # This means something went wrong.
        raise Exception('GET /ontop/ {}'.format(response.status_code))


def get_weight(scale_url):
    ### Get weight from scale
    url = scale_url + "/weight"

    try:
        response = requests.request('GET', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return None

    #print(response)

    if response.status_code == 200:
        weight = json.loads(response.text)
        #print(weight)
        # print('Weight', weight)
        return weight['weight']
    elif response.status_code == 500:
        return None
    else:
        # This means something went wrong.
        raise Exception('GET /weight/ {}'.format(response.status_code))


def get_scale_mac(scale_url):
    ### Get weight from scale
    url = scale_url + "/scaleaddr"

    try:
        response = requests.request('GET', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return None

    if response.status_code == 200:
        adress = json.loads(response.text)
        # print('Weight', weight)
        return adress['addr']
    elif response.status_code == 400:
        return None
    else:
        # This means something went wrong.
        raise Exception('GET /scaleaddr/ {}'.format(response.status_code))


def scale_connected(scale_url):
    ### Check if scale is initialized
    url = scale_url + "/connected"

    try:
        response = requests.request('GET', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return False

    # print('step on', response.status_code)

    if response.status_code == 200:
        return True
    elif response.status_code == 500:
        return False
    else:
        # This means something went wrong.
        raise Exception('GET /connected/ {}'.format(response.status_code))


def scale_authenticated(scale_url):
    ### Check if scale is initialized
    url = scale_url + "/authenticated"

    try:
        response = requests.request('PUT', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return False

    if response.status_code == 200:
        return True
    else:
        # This means something went wrong.
        raise Exception('PUT /authenticated/ {}'.format(response.status_code))


def reset_scale(scale_url):
    ### Reset weight and ontop variables
    url = scale_url + "/reset"

    try:
        response = requests.request('PUT', url, verify=verify_ssl)
    except Exception as e:
        print(e)
        return False

    if response.status_code == 200:
        return True
    elif response.status_code == 500:
        return False
    else:
        # This means something went wrong.
        raise Exception('PUT /reset/ {}'.format(response.status_code))


def set_standby(scale_url):
    url = scale_url + "/standby"

    try:
        response = requests.request('PUT', url, verify=verify_ssl)
        return True
    except Exception as e:
        print(e)
        return False

