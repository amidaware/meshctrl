import json
import websockets
import asyncio
from typing import Optional, Union, List, Dict
from . import utils


class MeshCtrl:
    """MeshCentral websocket client class.

    Attributes:
        url: A url string used to connect to the MeshCentral instance.
        headers: An optional set of headers to pass to websocket client.
    """
    # TODO: allow getting token in a file
    def __init__(
        self,
        loginkey: Optional[str] = None,
        token: Optional[str] = None,
        loginpass: Optional[str] = None,
        loginuser: str = "admin",
        logindomain: str = "",
        url: str = "wss://localhost:443",
    ):
        """Inits MeshCtrl with configuration

        Args:
            url (str):
                url used to connect to meshcentral instance. (default is wss://localhost:443).
            loginuser (str):
                login username for password authentication. (default is admin).
            loginkey (str, optional):
                Use hex login key to authenticate with meshcentral.
            token (str, optional):
                supply a 2fa token for login.
            loginpass (str, optional):
                login password for password authentication.
            logindomain (str):
                login domain for password authentication. (default is "").

        Raises:
            ValueError: If the required parameters are missing or misused.
        """

        self.headers = {}
        self.url = url

        # check for valid url
        if (
            len(self.url) < 5
            and not self.url.startswith("wss://")
            and not self.url.startswith("ws://")
        ):
            raise ValueError(f"Url parameter supplied is invalid: {url}")

        if not self.url.endswith("/"):
            self.url += "/control.ashx"
        else:
            self.url += "control.ashx"

        # make sure auth method is configured
        if not loginkey and not loginpass:
            raise ValueError(
                "You must configure either password or cookie authentication"
            )

        # check for password authentication
        if loginpass:
            self.headers = {
                "x-meshauth": utils.get_pwd_auth(loginuser, loginpass, token)
            }

        # check for cookie auth
        if loginkey:
            if len(loginkey) != 160:
                raise ValueError("The loginkey is invalid")
            self.url += (
                f"?auth={utils.get_auth_token(loginuser, loginkey, logindomain)}"
            )

    async def _websocket_call(self, data: Dict) -> Dict:
        """Initiates the websocket connection to mesh and returns the data.

        Args:
            data (Dict):
                The data passed to MeshCentral.

        Returns:
            Dict: MeshCentral Response.
        """

        async with websockets.connect(
            self.url, extra_headers=self.headers
        ) as websocket:
            await websocket.send(json.dumps(data))

            async for message in websocket:
                response = json.loads(message)

                if "responseid" in response:
                    if data["responseid"] == response["responseid"]:
                        return response
                else:
                    if data["action"] == response["action"]:
                        return response

    def _send(self, data: Dict) -> Dict:
        """Initiates asynchronous call"""

        return asyncio.run(self._websocket_call(data))

    def server_info(self) -> Dict:
        """Gets MeshCentral server info.

        Returns:
            Dict:
                Returns server info.
            
            Example:
                {
                    'domain': '', 
                    'name': 'mesh.example.com', 
                    'mpsname': 'mesh.example.com', 
                    'mpsport': 4433, 
                    'port': 4443, 
                    'emailcheck': True, 
                    'domainauth': False, 
                    'serverTime': 1645560067270, 
                    'features': 9607777, 
                    'features2': 16513, 
                    'languages': ['en', 'cs', 'da', 'de', 'es', 'fi', 'fr', 'hi', 'it', 'ja', 'ko', 'nl', 'nn', 'pl', 'pt-br', 'pt', 'ru', 'sv', 'tr', 'zh-chs', 'zh-cht'], 
                    'tlshash': '16D462CC0D306CFC7F242382A1606E2A57E6481B4EAAC7E5C6D91EFA306F9CABD0CD91566A8A35C3DA9580E1F51CF985', 
                    'agentCertHash': 'V7IZUeuuIWMCY8e1SIb8fKqM1RkS4fUmCbCZzi4cMMzHAi3EJPi9Y8CP5XQfz2tZ', 
                    'https': True, 
                    'redirport': 8080, 
                    'magenturl': 'mc://mesh.example.com:4443', 
                    'domainsuffix': '', 
                    'certExpire': 1652972190000
                }
        """

        data = {
            "action": "serverinfo"
        }

        return self._send(data)["serverinfo"] 

    def user_info(self) -> Dict:
        """Gets logged on user info.

        Returns:
            Dict:
                Returns current user info

            Example:
                {
                    '_id': 'user//username', 
                    'name': 'username', 
                    'creation': 1643754241, 
                    'links': {
                        'mesh//oAUeYE3HCqUFXWCkqwqfW@ElJ7orX6hrNv$r$RyCEsVgtUQNxYC6dLs4jlfQNTPA': {
                            'rights': 4294967295
                        }, 
                        'mesh//$lhtFH8ZYcVEZYSqLx1O2vxqgSdzX9bjZLAbmRMz3lJ@XLulbyhqeRUPF4MbaN64': {
                            'rights': 4294967295
                        }
                    }, 
                    'email': 'example@example.com', 
                    'emailVerified': True, 
                    'siteadmin': 4294967295, 
                    'pastlogin': 1645505345, 
                    'access': 1645558617, 
                    'login': 1645505346
                }
        """

        data = {
            "action": "userinfo"
        }

        return self._send(data)["userinfo"]

    def list_user_sessions(self) -> Dict:
        """List connected websockets users

        Returns:
            List:
                Returns list of users that are connected to websockets

            Example:
                {'user//tactical': 1}
        """     

        data = {
            "action": "wssessioncount",  
        }

        return self._send(data)["wssessions"]

    def get_device_group_id_by_name(self, group: str) -> Optional[str]:
        """Get the device group id by group name.

        Args:
            group (str):
                Used to search through device groups.

        Returns:
            str, None:
                Returns device group id if the device group exists otherwise returns None.
        """

        device_groups = self.list_device_groups()

        for device_group in device_groups:
            if device_group["name"] == group:
                return device_group["_id"]

        return None

    def device_group_exists(
        self, group: Optional[str] = None, id: Optional[str] = None
    ) -> bool:
        """Check if a device group exists by group name or id.

        This method needs either group or id arguments set. If both are set then group
        takes precedence.

        Args:
            group (str):
                Used to check if a device group with the same name exists.
            id (str):
                Used to check if a device group with the same id exists.

        Returns:
            bool: True or False depending on if the device group exists.
        """

        if not group and not id:
            raise ValueError("Arguments group or id must be specified")

        device_groups = self.list_device_groups()

        for device_group in device_groups:
            if device_group:
                if device_group["name"] == group:
                    return True
            elif id:
                if device_group["_id"] == id:
                    return True

        return False

    def list_device_groups(self, hex: bool = False) -> List[Dict]:
        """List device groups

        All device group ids returned from MeshCentral have a `mesh//`
        prepended. This function strips it so that other operations that use
        this don't have to.

        Args:
            hex (bool, optional): Converts the mesh ids to hex.

        Returns:
            List[Dict]: Mesh device groups.
        """

        data = {
            "action": "meshes",
        }

        device_groups = self._send(data)

        if hex:
            for group in device_groups["meshes"]:
                group["_id"] = utils.b64_to_hex(group["_id"].split("//")[1])
        else:
            for group in device_groups["meshes"]:
                group["_id"] = group["_id"].split("//")[1]

        return device_groups["meshes"]

    def add_device_group(
        self,
        name: str,
        desc: str = "",
        amt_only: bool = False,
        features: int = 0,
        consent: int = 0,
    ) -> Dict:
        """Add device group

        Args:
            name (str): Name of device group.
            desc (str, optional): Description of device group.
            amt_only (bool): Sets the group to AMT only. (default is false).
            features (int, optional):
                Optional features to enable for the device group. Sum of numbers below.
                    1. Auto-Remove
                    2. Hostname Sync
                    4. Record Sessions
            consent (int, optional):
                Optionally set the users consent for features. Sum of numbers below:
                    1. Desktop notify user
                    2. Terminal notify user
                    4. Files notify user
                    8. Desktop prompt user
                    16. Terminal prompt user
                    32. Files prompt user
                    64. Desktop toolbar

        Returns:
            Dict: Returns a confirmation that the device group was created

            Example:
                {
                    'action': 'createmesh',
                    'responseid': '259c3c66-8b74-4d0d-8d8b-a8a935220c1b',
                    'result': 'ok',
                    'meshid': 'mesh//a8tVU0ytXINDMaokjDPuGPimWQL0otT7YL0pOqgvV5wolzKsK$YnjB02GeuYDo1k',
                    'links': {'user//tactical': {'name': 'tactical', 'rights': 4294967295}}
                }
        """

        data = {
            "action": "createmesh",
            "meshname": name,
            "meshtype": 2 if not amt_only else 1,
            "desc": desc,
            "features": features,
            "consent": consent,
            "responseid": utils.gen_response_id(),
        }

        return self._send(data)

    def remove_device_group(
        self, id: Optional[str] = None, group: Optional[str] = None
    ) -> Dict:
        """Remove device group by group name or id

        This method needs either group or id arguments set. If both are set then group
        takes precedence.

        Args:
            group (str):
                Name of the device group to be deleted.
            id (str):
                Id of the device group to be deleted. Works with and without 'mesh//' in the id.

        Returns:
            Dict: Returns a confirmation that the device group was deleted.

            Example:
                {
                    'action': 'deletemesh',
                    'responseid': '53bc566e-2fe6-41ed-ae2e-8da25a4bff6c',
                    'result': 'ok'
                }
        """

        if not group and not id:
            raise ValueError("Arguments name or id must be specified")

        data = {"action": "deletemesh", "responseid": utils.gen_response_id()}

        if group:
            data["meshname"] = group
        elif id:
            data["meshid"] = id

        return self._send(data)

    # TODO: look into inviteCodes options
    def edit_device_group(
        self,
        id: Optional[str] = None,
        group: Optional[str] = None,
        name: Optional[str] = None,
        desc: Optional[str] = None,
        features: Optional[int] = None,
        consent: Optional[int] = None,
    ) -> Dict:
        """Edit device group by group name or id

        This method needs either group or id arguments set. If both are set then group
        takes precedence.

        Args:
            group (str):
                Name of the device group to be updated.
            id (str):
                Id of the device group to be updated. Works with and without 'mesh//' in the id.
            name (str, optional):
                New name for device group.
            desc (str, optional):
                New description for device group.
            features (int, optional):
                Change device group features. See add_device_group for options.
            consent (int, optional):
                Change consent options on device group. See add_device_group for options.

        Returns:
            Dict: Returns a confirmation that the device group was updated.

            Example:
                {
                    'action': 'editmesh',
                    'responseid': '3f560b80-7e97-43ba-8037-0ea1d3730ae2',
                    'result': 'ok'
                }
        """

        if not group and not id:
            raise ValueError("Arguments group or id must be specified")

        data = {"action": "editmesh", "responseid": utils.gen_response_id()}

        if group:
            data["meshidname"] = group
        elif id:
            data["meshid"] = id

        if name:
            data["meshname"] = name

        if desc:
            data["desc"] = desc

        if features:
            data["flags"] = features

        if consent:
            data["consent"] = consent

        return self._send(data)

    def get_user_id_by_name(self, username: str) -> Optional[str]:
        """Get the user account id by username.

        Args:
            username (str):
                Used to search through users.

        Returns:
            str, None:
                Returns the user account _id if the username exists otherwise returns None.
        """

        users = self.list_users()

        for user in users:
            if user["username"] == username:
                return user["_id"]

        return None

    def user_exists(
        self, username: Optional[str] = None, id: Optional[str] = None
    ) -> bool:
        """Check if a user account exists by username or id.

        This method needs either user or id arguments set. If both are set then name
        takes precedence.

        Args:
            username (str):
                Used to check if a device group with the same name exists.
            id (str):
                Used to check if a device group with the same id exists.

        Returns:
            bool: True or False depending on if the user account exists.
        """

        if not username and not id:
            raise ValueError("Arguments username or id must be specified")

        users = self.list_users()

        for user in users:
            if user:
                if user["name"] == username:
                    return True
            elif id:
                if user["_id"] == id:
                    return True

        return False

    def list_users(self) -> List[Dict]:
        """List users

        Returns:
            List[Dict]: Mesh user accounts.
        """

        data = {
            "action": "users"
        }

        return self._send(data)["users"]

    def add_user(
        self,
        username: str,
        password: Optional[str] = None,
        random_pass: bool = False,
        domain: Optional[str] = None,
        email: Optional[str] = None,
        email_verfied: bool = False,
        reset_pass: bool = False,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        rights: Optional[str] = None,
    ) -> Dict:
        """Add User

        This method needs a username set and password is optional only is random_pass is true. random_pass
        will take precedence.

        Args:
            username (str):
                Username for the user that is used to login
            password (str):
                Password to set for the user. Not needed if random_pass is set to True
            random_pass (str, optional):
                Sets a random password for the user account.
            domain (str, optional):
                Account domain, only for cross-domain admins.
            email (str, optional):
                New account email address.
            email_verified (bool, optional):
                New account email is verified.
            reset_pass (bool, optional):
                Request password reset on next login.
            full_name (str, optional):
                Set the full name for this account.
            phone (str, optional):
                Set the account phone number.
            rights (str, optional):
                Server permissions for account. Can be none, full, or a comma separated
                list of these possible values:
                manageusers,backup,restore,update,fileaccess,locked,nonewgroups,notools,usergroups,recordings,locksettings,allevents

        Returns:
            Dict: Returns a confirmation that the user was added

            Example:
                {
                    'action': 'adduser',
                    'responseid': '31424b26-9539-400d-ab41-e406aeb337b2',
                    'result': 'ok'
                }
        """

        if not password and not random_pass:
            raise ValueError("Either password or random_pass must be set")

        data = {
            "action": "adduser",
            "username": username,
            "pass": utils.gen_password() if random_pass else password,
            "responseid": utils.gen_response_id(),
        }

        if email:
            data["email"] = email
            if email_verfied:
                data["emailVerified"] = True

        if reset_pass:
            data["resetNextLogin"] = True

        if domain:
            data["domain"] = domain

        if phone:
            data["phone"] = phone

        if full_name:
            data["realname"] = full_name

        if rights:
            data["siteadmin"] = utils.user_permissions_str_to_int(rights)

        return self._send(data)

    def edit_user(
        self,
        username: str,
        domain: str = "",
        email: Optional[str] = None,
        email_verfied: bool = False,
        reset_pass: bool = False,
        full_name: Optional[str] = None,
        phone: Optional[str] = None,
        rights: Optional[str] = None,
    ) -> Dict:
        """Edit User

        This method needs a username set to identify the user to edit.

        Args:
            username (str):
                Username for the user that is used to login
            domain (str, optional):
                Account domain, only for cross-domain admins.  (defaults to '')
            email (str, optional):
                New account email address.
            email_verified (bool, optional):
                New account email is verified.
            reset_pass (bool, optional):
                Request password reset on next login.
            full_name (str, optional):
                Set the full name for this account.
            phone (str, optional):
                Set the account phone number.
            rights (str, optional):
                Server permissions for account. Can be none, full, or a comma separated
                list of these possible values:
                manageusers,backup,restore,update,fileaccess,locked,nonewgroups,notools,usergroups,recordings,locksettings,allevents

        Returns:
            Dict: Returns a confirmation that the user was edited

            Example:
                {
                    'action': 'edituser',
                    'responseid': '1d508225-818d-444c-9a33-62c4ef76f652',
                    'result': 'ok'
                }
        """

        data = {
            "action": "edituser",
            "userid": utils.format_user_id(username, domain),
            "responseid": utils.gen_response_id(),
        }

        if email:
            data["email"] = email
            if email_verfied:
                data["emailVerified"] = True

        if reset_pass:
            data["resetNextLogin"] = True

        if domain:
            data["domain"] = domain

        if phone:
            data["phone"] = phone

        if full_name:
            data["realname"] = full_name

        if rights:
            data["siteadmin"] = utils.permissions_str_to_int(rights)

        return self._send(data)

    def remove_user(self, username: str, domain: str = "") -> Dict:
        """Delete User

        This method needs a username set to identify the user to delete.

        Args:
            username (str):
                Username for the user that is used to login
            domain (str, optional)
                Account domain, only for cross-domain admins. (defaults to '')

        Returns:
            Dict: Returns a confirmation that the user was deleted.

            Example:
                {
                    'action': 'deleteuser',
                    'responseid': '1d508225-818d-444c-9a33-62c4ef76f652',
                    'result': 'ok'
                }
        """

        data = {
            "action": "deleteuser",
            "userid": utils.format_user_id(username, domain),
            "responseid": utils.gen_response_id(),
        }

        return self._send(data)

    def list_user_groups(self, json: bool = False) -> Union[List[Dict], Dict]:
        """List user groups

        Args:
            json (bool):
                Return a dictionary with the group id as the key. Can be
                useful for group lookup without iterating over all groups

        Returns:
            List[Dict] or Dict: Mesh user groups.
        """

        data = {
            "action": "usergroups"
        }

        if json:
            return self._send(data)["ugroups"]
        else:
            return [group for group in self._send(data)["ugroups"].values()]

    def add_user_group(self, name: str, desc: Optional[str] = None, domain: Optional[str] = None) -> Dict:
        """Add user group

        Args:
            name (str):
                Name of the user group.
            desc (str, optional):
                Description of user group.
            domain (str, optional):
                Domain of user group

        Returns:
            Dict: Returns confirmation that the user group was added.

            Example:
            {
                'action': 'createusergroup', 
                'responseid': '26100a76-0057-459d-9881-acf5fe357883', 
                'result': 'ok', 
                'ugrpid': 'ugrp//4nGnRRX@Ii9sL29TSYomnsZtRgDGKInE0d43HGsGposFtMwkBtxvYtsT6rX2XtdB', 
                'links': {}
            }
        """

        data = {
            "action": "createusergroup",
            "name": utils.format_usergroup_id(name, domain),
            "responseid": utils.gen_response_id(),
        }

        if desc:
            data["desc"] = desc
        if domain:
            data["domain"] = domain

        return self._send(data)

    def remove_user_group(self, group_id: str, domain: str = "") -> Dict:
        """Remove user group

        Args:
            group_id (str):
                Id of the user group.
            domain (str, optional)
                Domain for the user group

        Returns:
            Dict: Returns confirmation that the user group was removed.

            Example:
                {
                    'action': 'deleteusergroup', 
                    'responseid': '9f131710-2548-4607-ad7b-a1c2814c1c5c', 
                    'result': 'ok', 
                    'ugrpid': 'ugrp//HR5E2E9ax5hc$FD9hSFQKI7mKiknUjXy5r3Q$don5iOa2fMDTU0AwnsHCC8KHkNX'
                }
        """

        data = {
            "action": "deleteusergroup",
            "ugrpid": utils.format_usergroup_id(group_id, domain),
            "responseid": utils.gen_response_id(),
        }

        return self._send(data)

    def add_to_user_group(self, group_id: str, id: str, domain: str = "", rights: Optional[int] = 0) -> Dict:
        """Add to user group

        Add a user, device or device group to a user group.

        Args:
            group_id (str):
                Id of the user group. Can start with ugrp// or be just the name.
            id (str)
                Id of the user, device, or device group you are adding. Should start with
                user//, node//, or mesh//
            domain (str, optional)
                Domain of user group.
            rights (int, optional)
                Rights granted for adding device or device group.
                    - 4294967295 for full admin or the sum of the following numbers.
                    - 1 = Edit Device Group                2 = Manage Users
                    - 4 = Manage Computers                 8 = Remote Control
                    - 16 = Agent Console                   32 = Server Files
                    - 64 = Wake Device                     128 = Set Notes
                    - 256 = Remote View Only               512 = No Terminal
                    - 1024 = No Files                      2048 = No Intel AMT
                    - 4096 = Desktop Limited Input         8192 = Limit Events
                    - 16384 = Chat / Notify                32768 = Uninstall Agent
                    - 65536 = No Remote Desktop            131072 = Remote Commands
                    - 262144 = Reset / Power off 

        Returns:
            Dict: Returns confirmation that the user, device, or device group was added to user group.

            Example:
                {
                    'action': 'addusertousergroup', 
                    'responseid': 'aa09cc76-70f2-47b1-b680-92d4e363eaab', 
                    'result': 'ok', 
                    'added': 1, 
                    'failed': 0
                }
        """

        data = {
            "responseid": utils.gen_response_id(),
        }

        if id.startswith("user/"):
            data["action"] = "addusertousergroup"
            data["ugrpid"] = utils.format_usergroup_id(group_id, domain)
            data["usernames"] = [id.split("/")[2]]

        elif id.startswith("mesh/"):
            data["action"] = "addmeshuser"
            data["userid"] = utils.format_usergroup_id(group_id, domain)
            data["meshid"] = id
            data["meshadmin"] = rights if rights else 0

        elif id.startswith("node/"):
            data["action"] = "adddeviceuser"
            data["nodeid"] = utils.format_node_id(id)
            data["userids"] = [utils.format_usergroup_id(group_id, domain)]
            data["meshadmin"] = rights
        else:
            raise ValueError("The id is incorrect. Must start with mesh//, user//, or node//.")

        return self._send(data)    

    def remove_from_user_group(self, group_id: str, id: str, domain: str = "") -> Dict:
        """Remove from user group

        Remove a user, device or device group from a user group.

        Args:
            group_id (str):
                Id of the user group. Can start with ugrp// or be just the name.
            id (str)
                Id of the user, device, or device group you are adding. Should start with
                user//, node//, or mesh//
            domain (str, optional)
                Domain of user group.

        Returns:
            Dict: Returns confirmation that the user, device, or device group was removed from user group.

            Example:
                {
                    'action': 'removeuserfromusergroup', 
                    'responseid': '65243852-4480-400c-baae-d48ca313164e', 
                    'result': 'ok'
                }
        """

        data = {
            "responseid": utils.gen_response_id(),
        }

        if id.startswith("user/"):
            data["action"] = "removeuserfromusergroup"
            data["ugrpid"] = utils.format_usergroup_id(group_id, domain)
            data["userid"] = id

        elif id.startswith("mesh/"):
            data["action"] = "removemeshuser"
            data["userid"] = utils.format_usergroup_id(group_id, domain)
            data["meshid"] = id

        elif id.startswith("node/"):
            data["action"] = "adddeviceuser"
            data["nodeid"] = utils.format_node_id(id)
            data["userids"] = [utils.format_usergroup_id(group_id, domain)]
            data["meshadmin"] = 0
            data["remove"] = True
        else:
            raise ValueError("id must start with user/, mesh/, or node/")

        return self._send(data)   

    def move_to_device_group(self, group_id: str, dev_id: str, domain: str = "") -> Dict:
        """Move node to new device group

        Group_id can be the group name or full id. 

        Args:
            group_id (str):
                Name or id of the device group. Can start with mesh// or be just the name.
            dev_id (str)
                Id of the device you are moving.
            domain (str, optional)
                Domain of user group.

        Returns:
            Dict: Returns confirmation that the device was moved to device group.
        """

        data = {
            "action": "changeDeviceMesh",
            "responseid": utils.gen_response_id(),
            "nodeids": [utils.format_node_id(dev_id)],
            "meshid": utils.format_devicegroup_id(group_id, domain)
        }

        return self._send(data) 

    def add_user_to_device_group(self, group_id: str, user_id: str, domain: str = "", rights: Optional[int] = 0) -> Dict:
        """Add user to device group

        Args:
            group_id (str):
                Name or id of the device group. Can start with mesh// or be just the name.
            user_id (str)
                Id of the user you are adding.
            domain (str, optional)
                Domain of user group.
            rights (int, optional)
                Rights granted for adding device or device group.
                    - 4294967295 for full admin or the sum of the following numbers.
                    - 1 = Edit Device Group                2 = Manage Users
                    - 4 = Manage Computers                 8 = Remote Control
                    - 16 = Agent Console                   32 = Server Files
                    - 64 = Wake Device                     128 = Set Notes
                    - 256 = Remote View Only               512 = No Terminal
                    - 1024 = No Files                      2048 = No Intel AMT
                    - 4096 = Desktop Limited Input         8192 = Limit Events
                    - 16384 = Chat / Notify                32768 = Uninstall Agent
                    - 65536 = No Remote Desktop            131072 = Remote Commands
                    - 262144 = Reset / Power off 

        Returns:
            Dict: Returns confirmation that the user was added to device group.
        """

        data = {
            "action": "addmeshuser",
            "responseid": utils.gen_response_id(),
            "usernames": [utils.format_user_id(user_id, domain)],
            "meshadmin": rights,
            "meshid": utils.format_devicegroup_id(group_id, domain)
        }

        return self._send(data) 

    def remove_user_from_device_group(self, group_id: str, user_id: str, domain: str = "") -> Dict:
        """Remove user from device group

        Args:
            group_id (str):
                Name or id of the device group. Can start with mesh// or be just the name.
            user_id (str)
                Id of the user you are removing.
            domain (str, optional)
                Domain of user group.

        Returns:
            Dict: Returns confirmation that the user was removed from device group.
        """

        data = {
            "action": "removemeshuser",
            "responseid": utils.gen_response_id(),
            "usernames": [utils.format_user_id(user_id, domain)],
            "meshid": utils.format_devicegroup_id(group_id, domain)
        }

        return self._send(data) 

    def add_user_to_device(self, node_id: str, user_id: str, domain: str = "", rights: Optional[int] = 0) -> Dict:
        """Add user to device

        Args:
            node_id (str):
                id of device. Can start with node// or be just the name.
            user_id (str)
                Id of the user you are adding.
            domain (str, optional)
                Domain of user group.
            rights (int, optional)
                Rights granted for adding device or device group.
                    - 4294967295 for full admin or the sum of the following numbers.
                    - 1 = Edit Device Group                2 = Manage Users
                    - 4 = Manage Computers                 8 = Remote Control
                    - 16 = Agent Console                   32 = Server Files
                    - 64 = Wake Device                     128 = Set Notes
                    - 256 = Remote View Only               512 = No Terminal
                    - 1024 = No Files                      2048 = No Intel AMT
                    - 4096 = Desktop Limited Input         8192 = Limit Events
                    - 16384 = Chat / Notify                32768 = Uninstall Agent
                    - 65536 = No Remote Desktop            131072 = Remote Commands
                    - 262144 = Reset / Power off 

        Returns:
            Dict: Returns confirmation that the user was added to device.
        """

        data = {
            "action": "adddeviceuser",
            "responseid": utils.gen_response_id(),
            "usernames": [utils.format_user_id(user_id, domain)],
            "nodeid": utils.format_node_id(node_id, domain),
            "rights": rights
        }

        return self._send(data) 

    def remove_user_from_device(self, node_id: str, user_id: str, domain: str = "") -> Dict:
        """Add user to device

        Args:
            node_id (str):
                id of device. Can start with node// or be just the name.
            user_id (str)
                Id of the user you are removing.
            domain (str, optional)
                Domain of user group.

        Returns:
            Dict: Returns confirmation that the user was removed from device.
        """

        data = {
            "action": "adddeviceuser",
            "responseid": utils.gen_response_id(),
            "usernames": [utils.format_user_id(user_id, domain)],
            "nodeid": utils.format_node_id(node_id, domain),
            "rights": 0,
            "remove": True,
        }

        return self._send(data) 
    
    def list_devices(self, group_id: Optional[str] = None, domain: str = "", count: bool = False, details: bool = False, json: bool = False, filter: Optional[str] = None, filter_ids: Optional[List[str]] = None) -> Union[List[Dict], int, Dict]:
        """List devices

        List all devices or filter by a device group or filter by other properties

        Args:
            group_id (str, optional):
                id of group. Can start with mesh// or be just the name.
            domain (str, optional):
                Domain of the devices and device group
            count (bool, optional)
                Only return the device count
            json (bool, optional)
                Returns the json device list result instead of a list
            details (bool, optional):
                Show all device details in output
            filter_ids (List[str], optional):
                List of devices to filter by
            filter (str, optional):
                filter strings. accepted values below:
                    x                    - Devices with x in the name.
                    user:x or u:x        - Devices with x in the name of currently logged in user.
                    ip:x                 - Devices x IP address.
                    group:x or g:x       - Devices with x in device group name.
                    tag:x or t:x         - Devices with x in device tag.
                    atag:x or a:x        - Devices with x in device agent tag.
                    os:x                 - Devices with x in the device OS description.
                    amt:x                - Devices with Intel AMT provisioning state (0, 1, 2).
                    desc:x               - Devices with x in device description.
                    wsc:ok               - Devices with Windows Security Center ok.
                    wsc:noav             - Devices with Windows Security Center with anti-virus problem.
                    wsc:noupdate         - Devices with Windows Security Center with update problem.
                    wsc:nofirewall       - Devices with Windows Security Center with firewall problem.
                    wsc:any              - Devices with Windows Security Center with any problem.
                    a and b              - Match both conditions with precedence over OR. For example: lab and g:home.
                    a or b               - Math one of the conditions, for example: lab or g:home.

        Returns:
            Dict: Returns confirmation that the user was added to device.
        """

        data = {}

        if details:
            data["action"] = "getDeviceDetails"
        else:
            data["action"] = "nodes"

        if group_id:
            data["meshid"] = utils.format_devicegroup_id(group_id, domain)
        
        nodes = self._send(data)["nodes"]
        
        if filter_ids:
            for meshid in nodes:
                nodes[meshid] = [node for node in nodes[meshid] if node._id.split("/")[-1] in filter_ids]
        
        if filter:
            for meshid in nodes:
                nodes[meshid] = utils.parse_and_search_nodes(nodes, filter, device_groups=self.list_device_groups())
        
        if count:
            return len([node for sublist in nodes.values() for node in list])
        elif json:
            return nodes
        else:
            return [node for sublist in nodes.values() for node in list]

    def device_info(self, id: str) -> Dict:
        """Get device info

        Args:
            id (str):
                id of device. Can start with node// or be just the id.

        Returns:
            Dict: Returns information about the device
        """
        
        raise NotImplementedError() 

    def list_events(self):
        # TODO
        raise NotImplementedError() 

    def list_login_tokens(self):
        # TODO
        raise NotImplementedError() 

    def add_login_token(self):
        # TODO
        raise NotImplementedError() 

    def remove_login_token(self):
        # TODO
        raise NotImplementedError() 

    def broadcast_message(self):
        # TODO
        raise NotImplementedError()

    def remove_all_users_from_user_group(self):
        # TODO
        raise NotImplementedError()

    def send_invite_email(self):
        # TODO
        raise NotImplementedError()

    def generate_invite_link(self):
        # TODO
        raise NotImplementedError()

    def shell(self):
        # TODO
        raise NotImplementedError()

    def device_power(self):
        # TODO
        raise NotImplementedError()

    def device_sharing(self):
        # TODO
        raise NotImplementedError()

    def agent_download(self):
        # TODO
        raise NotImplementedError()

    def upload(self):
        # TODO
        raise NotImplementedError()

    def download(self):
        # TODO
        raise NotImplementedError()

    def device_open_url(self):
        # TODO
        raise NotImplementedError()

    def device_message(self):
        # TODO
        raise NotImplementedError()

    def device_toast(self):
        # TODO
        raise NotImplementedError()

    # run command on an agent
    def run_command(self, node_id: str, command: str, runAsUser: int = 0) -> Dict:

        data = {
            "action": "runcommands",
            "cmds": command,
            "nodeids": [f"node//{utils.b64_to_hex(node_id)}"],
            "runAsUser": runAsUser,
            "type": 1,
            "responseid": utils.gen_response_id(),
        }

        return self._send(data)
