#!/usr/bin/python3
import os, sys
import socket
import time
import datetime
import threading
import RPi.GPIO as GPIO
import signal
from uuid import getnode as get_mac
import subprocess
import pexpect

from packages import RPi_I2C_LCD, RPi_GPIO_keypad, OCARIOT_REST_API, scale_REST_API, NFC_reader
import ocariot_backup

# REST APIs URLs
scale_url = "http://localhost:4567"
ocariot_url = "https://iot.ocariot.unparallel.pt"

institution_initials = ''
minimum_student_id_length = 3

unlock_pin = '123456'
upload_pin = '654321'
network_pin = '147258'
nfc_pin = '789456'
delete_nfc_pin = '456789'
shutdown_pin = '000000'

ble_pair_jar = None

locked = True
backlight_on = True
allow_nfc = False  # allow to use read tag uid on get_child_id

# Automatically Lock after x seconds
autolock_timeout = 60  # 5 min

'''
LCD
'''
def init_lcd(lcd):
    padlock_chars = [
        # Char 0 - Padlock Locked
        [0x00, 0x1F, 0x11, 0x11, 0x1F, 0x1F, 0x1F, 0x1F],
        # Char 1 - Padlock Unlocked
        [0x1F, 0x11, 0x11, 0x01, 0x1F, 0x1F, 0x1F, 0x1F],
        # Char 2 - Wi-Fi Connected
        [0x00, 0x0E, 0x11, 0x04, 0x0A, 0x00, 0x04, 0x00],
        # Char 3 - Wi-Fi Disconnected
        [0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x00]
    ]

    lcd.lcd_load_custom_chars(padlock_chars)
    lcd.lcd_clear()


def lcd_clear_lines(lcd):
    lcd.lcd_display_string(''.center(20), 2)
    lcd.lcd_display_string(''.center(20), 3)
    lcd.lcd_display_string(''.center(20), 4)
    lcd_refresh_wifi_status(lcd)


def lcd_home(lcd):
    lcd.lcd_display_string(''.center(19), 1)
    lcd.lcd_display_string('LOCKED'.center(20), 2)
    lcd.lcd_display_string(''.center(20), 3)
    # lcd.lcd_display_string(chr(0).center(20), 4)
    lcd.lcd_display_string(''.ljust(10)+'unlock #'.rjust(10), 4)
    lcd_refresh_wifi_status(lcd)


def lcd_shutdown(lcd):
    lcd.lcd_display_string(''.center(19), 1)
    lcd.lcd_display_string(''.center(20), 2)
    lcd.lcd_display_string('SHUTTING'.center(20), 3)
    lcd.lcd_display_string(chr(0).center(20), 4)
    lcd_refresh_wifi_status(lcd)


def lcd_invalid_id(lcd):
    lcd.lcd_display_string('Invalid ID'.center(20), 3)
    time.sleep(1)
    lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)


def lcd_refresh_wifi_status(lcd):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        # requests.get(ocariot_url, verify=False)
        lcd.lcd_display_string_pos(chr(2), 1, 19)
    except:
        lcd.lcd_display_string_pos(chr(3), 1, 19)


class AnimateMessageThread(threading.Thread):
    def __init__(self, lcd, message):
        super().__init__()
        self._stop_event = threading.Event()
        self.daemon = True
        self.lcd = lcd
        self.message = message
        self.start()

    def run(self):
        # Clear line
        self.lcd.lcd_display_string(' '.center(20), 3)

        offset = int((20 - len(self.message)) / 2)
        self.lcd.lcd_display_string_pos(self.message, 3, offset)

        dots = ['   ', '.  ', '.. ', '...']

        while not self._stop_event.is_set():
            for dot in dots:
                self.lcd.lcd_display_string_pos(dot, 3, offset + len(self.message))
                time.sleep(0.3)
                if self._stop_event.is_set():
                    break

    def stop(self):
        self._stop_event.set()
        self.join()
        self.lcd.lcd_display_string(' '.center(20), 3)

    def stopped(self):
        return self._stop_event.is_set()


'''
Pair
'''


def scan(child):
    print("\nScanning devices...")
    child.sendline('scan on')
    child.expect(['Discovery started', 'failed'], timeout=3)
    time.sleep(5)
    child.sendline('scan off')
    child.expect('Discovery stopped', timeout=3)


def pair_addr(child, addr):
    print("Pairing " + addr)
    child.sendline('pair ' + addr)


def pair_ble(addr, kp=None, lcd=None):
    print("Initializing pairing process...")
    child = pexpect.spawn('bluetoothctl')

    global locked
    # Uncomment to enable debug output
    child.logfile = sys.stdout.buffer

    child.expect('Agent registered', timeout=5)
    #child.sendline('default-agent')
    #child.expect('agent request', timeout=5)

    #remove_addr(child, addr)
    #scan(child)
    pair_addr(child, addr)

    retries = 0
    while retries < 5:
        i = child.expect(
            ['Pairing successful', 'Enter passkey', 'Failed to pair', 'not available', 'Accept pairing', pexpect.EOF,
             pexpect.TIMEOUT])
        if i == 0:
            child.sendline('exit')
            print("Pairing successful")
            scale_REST_API.scale_authenticated(scale_url)
            return True

        elif i == 1:
            # Aks user input
            if kp is not None and lcd is not None:
                lcd_clear_lines(lcd)
                lcd.lcd_display_string('Scale PIN'.center(20), 2)
                scale_pin = get_pin(kp, lcd)
                while not scale_pin:
                    scale_pin = get_pin(kp, lcd)

                    if locked:
                        return
            else:
                scale_pin = input("Insert scale pin: ")
            child.sendline(scale_pin)
        elif i == 4:
            child.sendline('no')
            child.sendline('exit')
            print("Pairing successful")
            scale_REST_API.scale_authenticated(scale_url)
            return True
        else:
            print("Pairing failed. Retrying...")
            retries += 1
            #remove_addr(child, addr)
            #scan(child)
            pair_addr(child, addr)

    else:
        print("Error pairing scale bluetooth")
        child.sendline('exit')
        lcd.lcd_display_string('Error connecting'.center(20), 2)
        lcd.lcd_display_string('Try again'.center(20), 3)
        lcd.lcd_display_string('* back'.ljust(10)+'use id #'.rjust(10), 4)
        locked = True
    return False


'''
Keypad
'''


def get_digit(kp):
    # Loop while waiting for a keypress
    r = None
    t1 = None
    t = time.time()

    while r == None and time.time() - t < 1:
        r = kp.getKey()

    # Hold '*' for 1 second to lock scale
    if r == '*':
        if check_hold(kp, '*'):
            global locked
            locked = True
            return r

    # Debouncer
    elif r != None:
        while r == kp.getKey():
            pass

    return r


def check_hold(kp, key):
    r = kp.getKey()

    if r == key:
        t1 = time.time()
        while r == kp.getKey():
            if time.time() - t1 > 1:
                return True
    return False


'''
Gets
'''


def get_pin(kp, lcd):
    lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)
    lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)

    pin = []
    t = time.time()

    while time.time() - t < 10:
        d = get_digit(kp)

        # Press '*' to clear pin
        if d == '*':
            if len(pin) == 0:
                locked = True
                break
            else:
                pin.clear()
                lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)
                lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)
        # Press '#' to confirm pin
        elif d == '#' and len(pin) == 6:
            return ''.join(str(d) for d in pin)

        # Add digits to pin
        elif d != None and len(pin) < 6 and d != '#':
            pin.append(d)
            line = ('* ' * len(pin)) + ('_ ' * (6 - len(pin)))
            lcd.lcd_display_string(line.center(20), 3)
            lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)
            t = time.time()

    return None


def get_child_id(kp, lcd, nfc):
    lcd.lcd_display_string('Student ID'.center(20), 2)
    lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)

    global locked
    global read_nfc
    child_number = []
    t = time.time()
    read_nfc = False
    success = False
    global allow_nfc

    if allow_nfc:
        lcd.lcd_display_string('* back'.ljust(10)+'use nfc #'.rjust(10), 4)
    elif not allow_nfc:
        lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)



    while not locked:
        d = get_digit(kp)
        # Autolock keypad after a long period of inactivity
        if d != None:
            t = time.time()
        elif time.time() - t > autolock_timeout:
            print("Locking")
            locked = True
            return

        if check_hold(kp, '*'):
            locked = True
            read_nfc = not read_nfc
            return

       # Press '*' to clear student ID
        if d == '*':
            if len(child_number) == 0:
                locked = True
                break
            else:
                child_number.clear()
                lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)
                if allow_nfc:
                    lcd.lcd_display_string('* back'.ljust(10)+'use nfc #'.rjust(10), 4)
                elif not allow_nfc:
                    lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)

        # Press '#' to confirm student ID
        elif d == '#':
            if len(child_number) >= minimum_student_id_length:
                child_id = institution_initials + ''.join(str(d) for d in child_number)

                try:
                    child_info = OCARIOT_REST_API.head_children(ocariot_url, child_id)
                except:
                    return [1, child_id]

                if child_info:
                    return [1, child_id]
                else:
                    child_number.clear()
                    lcd_invalid_id(lcd)

            elif len(child_number) == 0:

                if allow_nfc == True:
                    read_nfc = not read_nfc

                    if read_nfc:
                        lcd.lcd_display_string('Reading NFC Tag'.center(20), 2)
                        lcd.lcd_display_string('Touch with bracelet'.center(20), 3)
                        lcd.lcd_display_string('* back'.ljust(10)+'use id #'.rjust(10), 4)

                        while read_nfc:

                            d = get_digit(kp)
                            if d == '*':
                                locked=True
                                read_nfc=False
                                allow_nfc=False

                            if d == '#':
                                read_nfc = not read_nfc
                                lcd.lcd_display_string('Student ID'.center(20), 2)
                                lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)
                                lcd.lcd_display_string('* back'.ljust(10)+'use nfc #'.rjust(10), 4)


                            success, tag_uid = nfc.get_uid()
                            if success:

                                t = time.time()

                                try:
                                    exists, child_info = OCARIOT_REST_API.get_child_username(ocariot_url, tag_uid)
                                except:
                                    return [2, tag_uid]

                                if exists:
                                    return [1, child_info['username']]
                                else:
                                    child_number.clear()
                                    lcd.lcd_display_string('No Children Found'.center(20), 3)
                                    time.sleep(1)
                                    lcd.lcd_display_string('_ _ _ _ _ _'.center(20), 3)
                                    lcd.lcd_display_string('* back'.ljust(10)+'use nfc #'.rjust(10), 4)



                            # Autolock keypad after a long period of inactivity
                            if d != None:
                                t = time.time()
                            elif time.time() - t > autolock_timeout:
                                locked = True
                                read_nfc = not read_nfc
                                return

                            if check_hold(kp, '*'):
                                locked = True
                                read_nfc = not read_nfc
                                return


            else:
                child_number.clear()
                lcd_invalid_id(lcd)

        # Add digits to student ID
        elif d != None and len(child_number) < 6:
            child_number.append(d)
            line = (' '.join(str(d) for d in child_number)) + (' _' * (6 - len(child_number)))
            lcd.lcd_display_string(line.center(20), 3)
            lcd.lcd_display_string('* clear'.ljust(10)+'ok #'.rjust(10), 4)


def get_weight(kp, lcd):
    th = AnimateMessageThread(lcd, 'Measuring')

    weight = None
    while not weight:
        if check_hold(kp, '*'):
            th.stop()
            return None

        weight = scale_REST_API.get_weight(scale_url)
        time.sleep(0.2)

    th.stop()
    return weight


'''
Interface
'''


def display_network(kp, lcd):
    lcd_clear_lines(lcd)
    lcd.lcd_display_string('NETWORK'.center(20), 1)
    lcd.lcd_display_string_pos(chr(2), 1, 19)

    lcd.lcd_display_string('* back'.ljust(10)+'next #'.rjust(10), 4)
    global locked
    locked = False

    t = time.time()
    option = 1

    while not locked:
        d = get_digit(kp)

        # Autolock keypad after a long period of inactivity
        if d != None:
            t = time.time()
        elif time.time() - t > autolock_timeout:
            locked = True
            return

        if d == '#':
            if option < 3:
                option = option + 1
            elif option == 3:
                option = 1

        if d == '*':
            locked = True
            break


        if option == 1:
            # Show SSID
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                ssid = os.popen("iwconfig wlan0 \
                                                        | grep 'ESSID' \
                                                        | awk '{print $4}' \
                                                        | awk -F\\\" '{print $2}'").read()
                lcd.lcd_display_string('SSID'.center(20), 2)
                lcd.lcd_display_string('{}'.format(ssid).center(20), 3)

            except:
                lcd.lcd_display_string('SSID'.center(20), 2)
                lcd.lcd_display_string('NOT CONNECTED'.center(20), 3)

        elif option == 2:
            # Show IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('10.255.255.255', 1))
                ipaddress = s.getsockname()[0]
                lcd.lcd_display_string('IP ADRESS'.center(20), 2)
                lcd.lcd_display_string('{}'.format(ipaddress).center(20), 3)
            except:
                lcd.lcd_display_string('IP ADRESS'.center(20), 2)
                lcd.lcd_display_string('NOT CONNECTED'.center(20), 3)
            finally:
                s.close()

        elif option == 3:
            try:
                mac = hex(get_mac())
                lcd.lcd_display_string('MAC ADDRESS'.center(20), 2)
                lcd.lcd_display_string('{}'.format(mac).center(20), 3)
            except:
                lcd.lcd_display_string('COULD NOT RETRIEVE'.center(20), 3)


def assign_nfc(kp, lcd, nfc):
    global locked
    locked = False
    global allow_nfc
    allow_nfc = False

    t = time.time()

    lcd_clear_lines(lcd)
    lcd.lcd_display_string('ASSIGN NFC Tag'.center(20), 1)
    lcd_refresh_wifi_status(lcd)
    lcd.lcd_display_string('* back'.ljust(10)+'ok #'.rjust(10), 4)

    while not locked:

        identifier = get_child_id(kp, lcd, nfc)

        if locked:
            return

        type = identifier[0]
        child_id = identifier[1]

        read_nfc = True

        while read_nfc and not locked:
            lcd.lcd_display_string('Reading NFC Tag'.center(20), 2)
            lcd_refresh_wifi_status(lcd)
            lcd.lcd_display_string('Approach bracelet'.center(20), 3)
            lcd.lcd_display_string('* back'.ljust(10)+''.rjust(10), 4)

            d = get_digit(kp)
            if d == '*':
                locked = True
                return

            success, tag_uid = nfc.get_uid()

            if not success:
                time.sleep(0.5)
                if check_hold(kp, '*'):
                    read_nfc = False

            if success:
                t = time.time()
                try:
                    res = OCARIOT_REST_API.post_nfc(ocariot_url, tag_uid, child_id)

                    if res == True:
                        read_nfc = False
                        lcd.lcd_display_string('NFC Tag Assigned'.center(20), 3)
                        time.sleep(2)
                    elif res == False:
                        lcd.lcd_display_string('Tag already in use'.center(20), 3)
                        read_nfc = False
                        time.sleep(2)

                except:
                    lcd.lcd_display_string('Error assigning'.center(20), 3)
                    read_nfc = False
                    time.sleep(2)


def delete_nfc(kp, lcd, nfc):
    global locked
    locked = False

    global allow_nfc
    allow_nfc = False

    t = time.time()

    lcd_clear_lines(lcd)
    lcd.lcd_display_string('Unassign NFC Tag'.center(20), 1)
    lcd_refresh_wifi_status(lcd)

    while not locked:

        identifier = get_child_id(kp, lcd, nfc)

        if locked:
            return
        type = identifier[0]
        child_id = identifier[1]

        read_nfc = True

        while read_nfc and not locked:

            lcd.lcd_display_string(' Reading NFC'.center(20), 2)
            lcd_refresh_wifi_status(lcd)
            lcd.lcd_display_string('Approach bracelet'.center(20), 3)

            d = get_digit(kp)

            # Autolock keypad after a long period of inactivity
            if d != None:
                t = time.time()
            elif time.time() - t > autolock_timeout:
                locked = True
                return

            if d == '*':
                locked = True
                read_nfc = False
                break

            success, tag_uid = nfc.get_uid()

            if not success:

                time.sleep(0.5)
                if check_hold(kp, '*'):
                    read_nfc = False

            if success:
                t = time.time()
                try:
                    res = OCARIOT_REST_API.delete_nfc(ocariot_url, tag_uid, child_id)

                    if res == True:
                        read_nfc = False
                        lcd.lcd_display_string('NFC Tag unassigned'.center(20), 3)
                        time.sleep(2)
                    elif res == False:
                        lcd.lcd_display_string('Tag is not associated'.center(20), 3)
                        read_nfc = False
                        time.sleep(2)

                except:
                    lcd.lcd_display_string('Error removing tag'.center(20), 3)
                    read_nfc = False
                    time.sleep(2)


def unlock_scale(kp, lcd):
    lcd.lcd_display_string(chr(1).center(20), 3)
    lcd.lcd_display_string('UNLOCKED'.center(20), 2)

    global locked
    global ble_pair_jar
    locked = False
    scale_addr = None
    initialized = None

    time.sleep(1)
    lcd_clear_lines(lcd)
    lcd.lcd_display_string('Connecting to scale'.center(20), 2)
    # th = AnimateMessageThread(lcd, 'Initializing')

    #start run ble_pair.jar
    if ble_pair_jar is not None:
        ble_pair_jar.kill()
        ble_pair_jar=None

    ble_pair_jar = subprocess.Popen(["java", "-jar", "/home/pi/ble_pair.jar"])


    # Set scale to connect
    while initialized == None:
        initialized = scale_REST_API.scale_initialized(scale_url)
        time.sleep(1)

    if locked:
        return

    if not initialized:

        # Wait for scale to be found
        while not scale_addr:
            scale_addr = scale_REST_API.get_scale_mac(scale_url)
            time.sleep(0.5)

        # Wait for scale to connect
        while not scale_REST_API.scale_connected(scale_url):
            time.sleep(0.5)

        if locked:
            return

        # Pair the scale
        if not pair_ble(scale_addr,kp,lcd):
            locked = True
            return

        lcd_clear_lines(lcd)
        lcd.lcd_display_string('Connecting to scale'.center(20), 2)

        # Check if scale is initialized
        while not scale_REST_API.scale_initialized(scale_url):
            time.sleep(0.5)

    # th.stop()


def run_scale(kp, lcd, nfc):
    # 1 username, 2 tag
    identifier = get_child_id(kp, lcd, nfc)

    global locked
    if locked:
        return

    child_id = identifier[1]
    type = identifier[0]

    lcd_clear_lines(lcd)
    th = AnimateMessageThread(lcd, 'Starting Scale')

    while not scale_REST_API.reset_scale(scale_url):
        time.sleep(0.5)
        if check_hold(kp, '*'):
            th.stop()
            return

    th.stop()

    lcd_clear_lines(lcd)
    lcd.lcd_display_string('Please step on scale'.center(20), 2)

    # Wait for someone to step on the scale
    while not scale_REST_API.child_on_scale(scale_url):
        time.sleep(0.5)
        if check_hold(kp, '*'):
            return

    lcd_clear_lines(lcd)

    weight = get_weight(kp, lcd)
    if weight != None:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

        # Try to post to OCARIOT Platform and save posts to successful or failed backup files
        try:
            confirmed = False
            if type == 1:
                res = OCARIOT_REST_API.post_weight(ocariot_url, child_id, weight, timestamp)
                print('Success!', res)

                lcd_clear_lines(lcd)
                lcd.lcd_display_string('Measurement complete'.center(20), 3)
                lcd.lcd_display_string(''.ljust(10) + ' confirm #'.rjust(10), 4)
                time.sleep(2)


                while confirmed == False:
                    d = get_digit(kp)
                    if d == '#':
                        confirmed = True
                        break


            elif type == 2:
                res = OCARIOT_REST_API.post_weight_nfc(ocariot_url, child_id, weight, timestamp)
                print('Success!', res)

                lcd_clear_lines(lcd)
                lcd.lcd_display_string('Measurement complete'.center(20), 3)
                lcd.lcd_display_string(''.ljust(10) + ' confirm #'.rjust(10), 4)
                time.sleep(2)

                while confirmed == False:
                    d = get_digit(kp)
                    if d == '#':
                        confirmed=True
                        break

        except:
            confirmed = False
            if type == 1:
                backup_post = {'child_number': child_id, 'weight': weight, 'timestamp': timestamp, 'type': type}
                ocariot_backup.backup_failed(backup_post)
                print('Failed!', backup_post)

                lcd_clear_lines(lcd)
                lcd.lcd_display_string('Failed to upload'.center(20), 1)
                lcd.lcd_display_string('Weight saved locally'.center(20), 2)
                lcd.lcd_display_string(''.ljust(10) + ' confirm #'.rjust(10), 4)
                time.sleep(2)

                while confirmed == False:
                    d = get_digit(kp)
                    if d == '#':
                        confirmed=True
                        break

            elif type == 2:
                backup_post = {'tag_uid': child_id, 'weight': weight, 'timestamp': timestamp, 'type': type}
                ocariot_backup.backup_failed(backup_post)
                print('Failed!', backup_post)

                lcd_clear_lines(lcd)
                lcd.lcd_display_string('Failed to upload'.center(20), 1)
                lcd.lcd_display_string('Weight saved locally'.center(20), 2)
                lcd.lcd_display_string(''.ljust(10) + ' confirm #'.rjust(10), 4)
                time.sleep(2)

                while confirmed == False:
                    d = get_digit(kp)
                    if d == '#':
                        confirmed=True
                        break



def run_scale_interface(kp, lcd, nfc):
    while True:
        lcd_home(lcd)

        global locked, ble_pair_jar
        global backlight_on
        global allow_nfc
        t = time.time()
        if locked:

            if ble_pair_jar is not None:
                ble_pair_jar.send_signal(signal.SIGINT)
                ble_pair_jar = None

            # Press '#' to unlock scale
            d = get_digit(kp)
            while d != '#':
                time.sleep(0.1)
                d = get_digit(kp)

                if d != None:
                    t = time.time()


                # Turn off backlight after 30 seconds of inactivity
                if backlight_on and time.time() - t > 30:
                    lcd.lcd_clear()
                    lcd.backlight(0)
                    backlight_on = False
                    scale_REST_API.reset_scale(scale_url)
                    # scale_REST_API.set_standby(scale_url)

                elif not backlight_on and d != None:
                    lcd_home(lcd)
                    backlight_on = True

            # Insert Pin to unlock scale or upload failed posts
            lcd.lcd_display_string('Unlock PIN'.center(20), 2)
            pin = get_pin(kp, lcd)
            if pin:

                # Shutdown
                if pin == shutdown_pin:
                    lcd_shutdown(lcd)
                    time.sleep(10)
                    #os.system('rm ' + "/tmp/ble_gatt-rest-api-server/data.db")
                    lcd_clear_lines(lcd)
                    lcd.backlight(0)
                    subprocess.call("shutdown -h now", shell=True)
                    sys.exit(1)

                # Unlock
                if pin == unlock_pin:
                    allow_nfc = True
                    unlock_scale(kp, lcd)

                # Upload failed posts
                elif pin == upload_pin:
                    th = AnimateMessageThread(lcd, 'Uploading')
                    res = ocariot_backup.upload_failed_posts(ocariot_url)
                    th.stop()

                    if res == 0:
                        lcd.lcd_display_string('Upload Done'.center(20), 2)
                    elif res == -2:
                        lcd.lcd_display_string('Nothing to Upload'.center(20), 2)
                    else:
                        lcd.lcd_display_string('Upload Failed'.center(20), 2)

                    time.sleep(1)
                    lcd_clear_lines(lcd)

                # Associate NFC tag Uid with child id
                elif pin == nfc_pin:
                    assign_nfc(kp, lcd, nfc)

                elif pin == delete_nfc_pin:
                    delete_nfc(kp, lcd, nfc)

                elif pin == network_pin:
                    display_network(kp, lcd)

                # Invalid Pin
                else:
                    lcd.lcd_display_string('Invalid Pin'.center(20), 2)
                    time.sleep(1)
                    continue

        # While unlocked get Student IDs, measure weights and upload to OCARIOT Platform
        while not locked:
            run_scale(kp, lcd, nfc)


def exit_cleanup():
    lcd = RPi_I2C_LCD.lcd()
    lcd.lcd_clear()
    lcd.backlight(0)
    GPIO.cleanup()


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


# ----------------- MAIN -----------------
def main():
    kp = RPi_GPIO_keypad.keypad(columnCount=3)
    lcd = RPi_I2C_LCD.lcd()
    nfc = NFC_reader.nfc()

    init_lcd(lcd)

    # Catch shutdown signal and power off the LCD
    signal.signal(signal.SIGTERM, sigterm_handler)

    run_scale_interface(kp, lcd, nfc)


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
    finally:
        exit_cleanup()
