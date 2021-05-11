#!/usr/bin/python3
import time
import binascii

from pn532pi import Pn532, pn532
from pn532pi import Pn532I2c


class nfc():
    def __init__(self):
        self.PN532_I2C = Pn532I2c(0)
        self.nfc = Pn532(self.PN532_I2C)
        self.setup()

    def setup(self):
        self.nfc.begin()

        versiondata = self.nfc.getFirmwareVersion()
        if (not versiondata):
            print("Didn't find PN53x board")
            raise RuntimeError("Didn't find PN53x board")  # halt

        #  Got ok data, print it out!
        print("Found chip PN5 {:#x} Firmware ver. {:d}.{:d}".format((versiondata >> 24) & 0xFF,
                                                                    (versiondata >> 16) & 0xFF,
                                                                    (versiondata >> 8) & 0xFF))

        #  configure board to read RFID tags
        self.nfc.SAMConfig()


    def get_uid(self):
        #  Wait for an ISO14443A type cards (Mifare, etc.).  When one is found
        #  'uid' will be populated with the UID, and uidLength will indicate
        #  if the uid is 4 bytes (Mifare Classic) or 7 bytes (Mifare Ultralight)
        success, uid = self.nfc.readPassiveTargetID(pn532.PN532_MIFARE_ISO14443A_106KBPS)

        return success,binascii.hexlify(bytearray(uid)).decode('utf8')
