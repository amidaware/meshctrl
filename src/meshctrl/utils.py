import time
import uuid
from base64 import b64encode
import random
import string

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes


def get_pwd_auth(username: str, password: str, token: str = None) -> str:
    token_string = f", {str_to_b64(token)}" if token else ""
    return f"{str_to_b64(username)}, {str_to_b64(password)}{token_string}"


def get_auth_token(user: str, key: str, domain: str = "") -> str:
    key = bytes.fromhex(key)
    key1 = key[0:32]
    msg = '{{"userid":"{}", "domainid":"{}", "time":{}}}'.format(
        f"{format_user_id(user, domain)}", domain, int(time.time())
    )
    iv = get_random_bytes(12)

    a = AES.new(key1, AES.MODE_GCM, iv)
    msg, tag = a.encrypt_and_digest(bytes(msg, "utf-8"))

    return b64encode(iv + tag + msg, altchars=b"@$").decode("utf-8")


def b64_to_hex(hex: str) -> str:
    return b64encode(bytes.fromhex(hex)).decode().replace(r"/", "$").replace(r"+", "@")


def str_to_b64(string):
    return str(b64encode(string.encode("utf-8")), "utf-8")


def gen_response_id() -> str:
    return str(uuid.uuid4())


def gen_password() -> str:
    return str(
        random.sample(
            string.ascii_lowercase + string.ascii_uppercase + string.digits, 7
        )
    )


def permissions_str_to_int(perms: str) -> int:
    site_perms = 0x00000000
    perms_list = perms.lower().split(",")
    for perm in perms_list:
        if perm == "none":
            break
        elif perm == "full":
            site_perms = 0xFFFFFFFF
            break
        elif perm == "backup":
            site_perms |= 0x00000001
        elif perm == "manageusers":
            site_perms |= 0x00000002
        elif perm == "restore":
            site_perms |= 0x00000004
        elif perm == "fileaccess":
            site_perms |= 0x00000008
        elif perm == "update":
            site_perms |= 0x00000010
        elif perm == "locked":
            site_perms |= 0x00000020
        elif perm == "nonewgroups":
            site_perms |= 0x00000040
        elif perm == "notools":
            site_perms |= 0x00000080
        elif perm == "usergroups":
            site_perms |= 0x00000100
        elif perm == "recording":
            site_perms |= 0x00000200
        elif perm == "locksettings":
            site_perms |= 0x00000400
        elif perm == "allevents":
            site_perms |= 0x00000800

    return int(site_perms)


def format_user_id(username, domain=""):
    if "user/" not in username:
        return f"user/{domain}/{username}"
    else:
        return username
