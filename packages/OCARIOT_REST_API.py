
import os, sys
import requests
import json
import subprocess


# Disable SSL verification and warnings
import urllib3
urllib3.disable_warnings()
verify_ssl = False

CLIENT_CERT_PATH = "/home/pi/scale-keypad/certificate.crt"
CLIENT_KEY_PATH = "/home/pi/scale-keypad/private.key"
CA_CERT_PATH = "/home/pi/scale-keypad/ca.crt"

institution_id="5f5212dbd9b19e006aade54b"
device_id="5f5218ce9a1cb301163d61a8"

### Get children username by NFC Tag UID
def get_child_username(ocariot_url, tag_uid):

    url = ocariot_url + "/v1/children/nfc/" + tag_uid

    payload={}

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('GET', url, headers=headers, data=payload, verify=CA_CERT_PATH,
                                cert=(CLIENT_CERT_PATH, CLIENT_KEY_PATH))
    res = json.loads(response.text)

    if response.status_code == 200:
        return True,res
    elif response.status_code == 404:
        return False,res
    else:
        # This means something went wrong.
        raise Exception('GET /children/nfc {}'.format(response.status_code))

### Confirm children exist by username
def head_children(ocariot_url, child_username):

    url = ocariot_url + "/v1/children/" + child_username

    payload = {}

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('HEAD', url, headers=headers, data=payload, verify=CA_CERT_PATH, cert=(CLIENT_CERT_PATH,CLIENT_KEY_PATH))

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    else:
        # This means something went wrong.
        raise Exception('HEAD /v1/children/ {}'.format(response.status_code))


### Send weight measurement
def post_weight(ocariot_url, child_username, weight, timestamp):

    url = ocariot_url + "/v1/children/" + child_username + "/weights"

    payload = "{\n  \"timestamp\": \"" + timestamp + "\",\n  \"value\": " + str(weight) + ",\n  \"unit\": \"kg\"\n}"

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('POST', url, headers=headers, data=payload, verify=CA_CERT_PATH, cert=(CLIENT_CERT_PATH,CLIENT_KEY_PATH))

    if response.status_code == 201:
        res = json.loads(response.text)
        # print(json.dumps(res, indent=4))
        return res
    elif response.status_code == 409:
        # Conflict - value already inserted
        return 409
    else:
        # This means something went wrong.
        raise Exception('POST /children/weights {}'.format(response.status_code))

### Send weight measurement with nfc
def post_weight_nfc(ocariot_url, tag_uid, weight, timestamp):

    url = ocariot_url + "/v1/children/nfc/" + tag_uid + "/weights"

    payload = "{\n  \"timestamp\": \"" + timestamp + "\",\n  \"value\": " + str(weight) + ",\n  \"unit\": \"kg\"\n}"

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('POST', url, headers=headers, data=payload, verify=CA_CERT_PATH, cert=(CLIENT_CERT_PATH,CLIENT_KEY_PATH))

    if response.status_code == 201:
        res = json.loads(response.text)
        # print(json.dumps(res, indent=4))
        return res
    elif response.status_code == 409:
        # Conflict - value already inserted
        return 409
    else:
        # This means something went wrong.
        raise Exception('POST /v1/children/nfc/ {}'.format(response.status_code))

##Associate NFC tag with children
def post_nfc(ocariot_url, nfc_uid, child_username):

    url = ocariot_url + "/v1/children/" + child_username + "/nfc"

    payload = "{\n  \"nfc_tag\": \"" + nfc_uid + "\"\n}"

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('POST', url, headers=headers, data=payload, verify=CA_CERT_PATH, cert=(CLIENT_CERT_PATH,CLIENT_KEY_PATH))


    if response.status_code == 204:
        #print(json.dumps(res, indent=4))
        return True
    elif response.status_code == 409:
        # Conflict - Tag already associated with another user
        return False
    else:
        # This means something went wrong.
        raise Exception('POST /v1/children/username/nfc {}'.format(response.status_code))

def delete_nfc(ocariot_url, nfc_uid, child_username):

    url = ocariot_url + "/v1/children/" + child_username + "/nfc"

    payload = "{\n  \"nfc_tag\": \"" + nfc_uid + "\"\n}"

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('DELETE', url, headers=headers, data=payload, verify=CA_CERT_PATH,
                                cert=(CLIENT_CERT_PATH, CLIENT_KEY_PATH))

    if response.status_code == 204:
        #print(json.dumps(res, indent=4))
        return True
    elif response.status_code == 409:
        # Conflict - Tag already associated with another user
        return False
    else:
        # This means something went wrong.
        raise Exception('DELETE /v1/children/username/nfc {}'.format(response.status_code))

def renew_certificate(ocariot_url):

    url = ocariot_url + "/v1/institutions/" + institution_id + "/devices/" + device_id + "/pki/renew"

    payload = {}

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request('POST', url, headers=headers, data=payload, verify=CA_CERT_PATH, cert=(CLIENT_CERT_PATH, CLIENT_KEY_PATH))

    if response.status_code == 201:
        res = json.loads(response.text)
        return res
    else:
        # This means something went wrong.
        res = json.loads(response.text)
        raise Exception(res['description'])


# ----------------- MAIN -----------------
def main():
    # OCARIOT REST Credentials
    username = 'UI-scale'
    password = 'uiuiui123'
    ocariot_url = "https://api.ocariot.lst.tfo.upm.es"

    child_info = get_children(ocariot_url, 'UI234567')

    result = post_weight(ocariot_url,child_info['id'], 35.6)




if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nShutdown requested! Exiting...')
        sys.exit(0)
    except Exception:
        print('\nAn error occurred! Exiting...\n')
        import traceback
        traceback.print_exc()
        sys.exit(1)
