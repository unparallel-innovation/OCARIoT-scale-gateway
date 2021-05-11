import sys

import OpenSSL
import time
from datetime import datetime
from packages import OCARIOT_REST_API

ocariot_url="https://iot.ocariot.tk"

def pyopenssl_check_expiration():
    ''' Return the numbers of day before expiration. False if expired.'''

    c = OpenSSL.crypto
    certificate = c.load_certificate(c.FILETYPE_PEM, open(OCARIOT_REST_API.CLIENT_CERT_PATH).read())
    certificate_remaining_date = datetime.datetime.strptime(str(certificate.get_notAfter()), "b'%Y%m%d%H%M%SZ'")
    return certificate_remaining_date


# ----------------- MAIN -----------------
def main():

     while True:

        today=datetime.today()
        expiration_date=pyopenssl_check_expiration()
        difference=expiration_date-today

        if difference.days<30:

            res=OCARIOT_REST_API.renew_certificate(ocariot_url)

            try:
                cert=res["certificate"]
                certificate_file = open(OCARIOT_REST_API.CLIENT_CERT_PATH, "w+")
                certificate_file.write(cert)
                certificate_file.close()
            except Exception as e:
                raise Exception(e)

        time.sleep(86400)#1 day


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('\nAn error occurred! Exiting...\n')
        import traceback
        traceback.print_exc()
        sys.exit(1)