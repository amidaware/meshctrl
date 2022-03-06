import time
import uuid
from base64 import b64encode
import random
import string
import re
from typing import Dict, List, Optional

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


def user_permissions_str_to_int(perms: str) -> int:
    site_perms = 0
    if "none" in perms:
        return 0
    elif "full" in perms:
        return 0xFFFFFFFF
    elif "backup" in perms:
        site_perms |= 1
    elif "manageusers" in perms:
        site_perms |= 2
    elif "restore" in perms:
        site_perms |= 4
    elif "fileaccess" in perms:
        site_perms |= 8
    elif "update" in perms:
        site_perms |= 16
    elif "locked" in perms:
        site_perms |= 32
    elif "nonewgroups" in perms:
        site_perms |= 64
    elif "notools" in perms:
        site_perms |= 128
    elif "usergroups" in perms:
        site_perms |= 256
    elif "recording" in perms:
        site_perms |= 512
    elif "locksettings" in perms:
        site_perms |= 1024
    elif "allevents" in perms:
        site_perms |= 2048

    return int(site_perms)


def devicegroup_permissions_str_to_int(perms: str) -> int:
    rights = 0
    if "fullrights" in perms:
        return 0xFFFFFFFF
    if "editgroup" in perms:
        rights |= 1
    if "manageusers" in perms:
        rights |= 2
    if "managedevices" in perms:
        rights |= 4
    if "remotecontrol" in perms:
        rights |= 8
    if "agentconsole" in perms: 
        rights |= 16
    if "serverfiles" in perms:
        rights |= 32
    if "wakedevices" in perms:
        rights |= 64
    if "notes" in perms:
        rights |= 128
    if "desktopviewonly" in perms:
        rights |= 256
    if "noterminal" in perms:
        rights |= 512
    if "nofiles" in perms:
         rights |= 1024
    if "noamt"  in perms:
        rights |= 2048
    if "limiteddesktop" in perms:
        rights |= 4096
    if "limitedevents" in perms:
        rights |= 8192
    if "chatnotify" in perms:
        rights |= 16384
    if "uninstall" in perms:
        rights |= 32768

    return rights


def format_user_id(username: str, domain="") -> str:
    if "user/" not in username:
        return f"user/{domain}/{username}"
    else:
        return username


def format_usergroup_id(group: str, domain="") -> str:
    if "ugrp/" not in group:
        return f"ugrp/{domain}/{group}"
    else:
        return group


def format_devicegroup_id(group: str, domain="") -> str:
    if "mesh/" not in group:
        return f"ugrp/{domain}/{group}"
    else:
        return group

def format_node_id(node: str, domain="") -> str:
    if "node/" not in node:
        return f"node/{domain}/{node}"
    else:
        return node

def parse_and_search_nodes(nodes: List[Dict], filter: str, device_groups: Dict) -> List[Dict]:
    results = []
    filters = filter.split(" or ")
    for f in filters:
        or_results = parse_search_and_input(nodes, f)
        if not results:
            results = or_results
        else:
            results = [node for node in or_results if node in results]


def parse_search_and_input(nodes: List[Dict], f: str, device_groups: Dict) -> List[Dict]:
    filters = filter.split(" and ")
    results = []
    for f in filters:
        and_results = filter_devices_by_filter(nodes, f)
        if not results:
            results = and_results
        else:
            results = [node for node in and_results if node in results]
    return results

def filter_devices_by_filter(nodes: List[Dict], f: str, device_groups: Dict) -> List[Dict]:
    results = []
    user_search = f[5:] if f.startsWith("user:".lower()) else None
    user_search = f[2:] if f.startsWith("u:".lower()) else None
    ip_search = f[3:] if f.startsWith("ip:".lower()) else None
    group_search = f[6:] if f.startsWith("group:".lower()) else None
    group_search = f[2:] if f.startsWith("g:".lower()) else None
    tag_search = f[4:] if f.startsWith("tag:".lower()) else None
    tag_search = f[2:] if f.startsWith("t:".lower()) else None
    agent_tag_search = f[5:] if f.startsWith("atag:".lower()) else None
    os_search = f[3:] if f.startsWith("os:".lower()) else None
    amt_search = f[4:] if f.startsWith("amt:".lower()) else None
    desc_search = f[5:] if f.startsWith("desc:".lower()) else None
    wsc_search = None
    if f == "wsc:ok":
        wsc_search = 1
    elif f == "wsc:noav":
        wsc_search = 2
    elif f == "wsc:noupdate":
        wsc_search = 3
    elif f == "wsc:nofirewall":
        wsc_search = 4
    elif f == "wsc:any":
        wsc_search = 5
    
    if f == "":
        results = nodes
    elif ip_search:
        results = [node for node in nodes if node["ip"] and ip_search in node["ip"]]
    elif group_search:
        if device_groups:
            results = [node for node in nodes if group_search in device_groups[node["meshid"]].name]
    elif tag_search or tag_search == "":
        results = [node for node in nodes if ((node["agent"] and not node["agent"]["tag"]) and tag_search == "") or (node["agent"] and node["agent"]["tag"] and node["agent"]["tag"].lower() in tag_search)]
    elif agent_tag_search or agent_tag_search == "":
        results = [node for node in nodes if (node["agent"] and node["agent"]["tag"] and agent_tag_search == "") or (node["agent"] and node["agent"]["tag"] and node["agent"]["tag"].lower() in agent_tag_search)]
    elif user_search:
        results = [node for node in nodes if node["users"] and user_search in node["users"]]
    elif os_search:
        results = [node for node in nodes if node["osdesc"] and os_search in node["osdesc"].lower()]
    elif amt_search or amt_search == "":
        results = [node for node in nodes if (node["intelamt"] and amt_search == "") or node["intelamt"]["state"] == amt_search]
    elif desc_search or desc_search == "":
        results = [node for node in nodes if ("desc" in node["desc"].keys() and node["desc"] != "" and (desc_search == "" or desc_search in node["desc"]))]
    elif wsc_search:
        for node in nodes:
            if wsc_search == 1 and node["wsc"]["antiVirus"] == "OK" and node["wsc"]["autoUpdate"] == "OK" and node["wsc"]["firewall"] == "OK":
                results.append(node)
            elif (wsc_search == 2 or wsc_search == 5) and (node["wsc"]["antiVirus"] != "OK"):
                results.append(node)
            elif (wsc_search == 3 or wsc_search == 5) and (node["autoUpdate" != "OK"]):
                results.append(node)
            elif (wsc_search == 4 or wsc_search == 5) and (node["wsc"]["firewall"] != "OK"):
                results.append(node)
    else:
        regex = re.compile("|".join(re.split(r"/\s+/", f)))
        results = [node for node in nodes if regex.search(node["name"].lower())]

    return results