# rfid_reader.py
#
# Fully non-blocking RFID reader for MFRC522
# Safe to use with background threads
# No infinite loops, no blocking waits

from mfrc522 import MFRC522

# Create ONE global RFID reader instance
# (Much safer and faster than creating a new one every read)
reader = MFRC522()


def read_rfid():
    """
    Attempts a single RFID read (non-blocking).
    Returns:
    - UID string if a card is detected
    - None if no card is present
    """

    try:
        # Try one request
        (status, tag_type) = reader.request(reader.REQIDL)
        if status != reader.OK:
            return None

        # Try one anticollision read
        (status, uid) = reader.anticoll()
        if status != reader.OK:
            return None

        # Convert UID array to one string
        uid_str = "".join(str(x) for x in uid)
        return uid_str

    except Exception as e:
        # Prevent crashes if the RFID reader throws an exception
        print("RFID read error:", e)
        return None
