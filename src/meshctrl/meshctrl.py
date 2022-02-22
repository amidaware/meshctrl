import json
import websockets
import asyncio
from typing import Optional
from . import utils


class MeshCtrl:
    """MeshCentral websocket client class.

    Attributes:
        url: A url string used to connect to the MeshCentral instance.
        headers: An optional set of headers to pass to websocket client.
    """

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

    async def _websocket_call(self, data: dict) -> dict:
        """Initiates the websocket connection to mesh and returns the data.

        Args:
            data (dict):
                The data passed to MeshCentral.

        Returns:
            dict: MeshCentral Response.
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

    def _send(self, data: dict) -> dict:
        """Initiates asynchronous call"""

        return asyncio.run(self._websocket_call(data))

    def server_info(self) -> dict:
        """Gets MeshCentral server info.

        Returns:
            dict:
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

    def user_info(self) -> dict:
        """Gets logged on user info.

        Returns:
            dict:
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

    def list_device_groups(self, hex: bool = False) -> list:
        """List device groups

        All device group ids returned from MeshCentral have a `mesh//`
        prepended. This function strips it so that other operations that use
        this don't have to.

        Args:
            hex (bool, optional): Converts the mesh ids to hex.

        Returns:
            list: Mesh device groups.
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

    # TODO: Don't create device group if name already exists
    def add_device_group(
        self,
        name: str,
        desc: str = "",
        amt_only: bool = False,
        features: int = 0,
        consent: int = 0,
    ) -> dict:
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
            dict: Returns a confirmation that the device group was created

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
    ) -> dict:
        """Remove device group by group name or id

        This method needs either group or id arguments set. If both are set then group
        takes precedence.

        Args:
            group (str):
                Name of the device group to be deleted.
            id (str):
                Id of the device group to be deleted. Works with and without 'mesh//' in the id.

        Returns:
            dict: Returns a confirmation that the device group was deleted.

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
    # TODO: Don't create device group if name already exists
    def edit_device_group(
        self,
        id: Optional[str] = None,
        group: Optional[str] = None,
        name: Optional[str] = None,
        desc: Optional[str] = None,
        features: Optional[int] = None,
        consent: Optional[int] = None,
    ) -> dict:
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
            dict: Returns a confirmation that the device group was updated.

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

    def list_users(self) -> list:
        """List users

        Returns:
            list: Mesh user accounts.
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
    ) -> dict:
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
            dict: Returns a confirmation that the user was added

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
            data["siteadmin"] = utils.permissions_str_to_int(rights)

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
    ) -> dict:
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
            dict: Returns a confirmation that the user was edited

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

    def remove_user(self, username: str, domain: str = "") -> dict:
        """Delete User

        This method needs a username set to identify the user to delete.

        Args:
            username (str):
                Username for the user that is used to login
            domain (str, optional)
                Account domain, only for cross-domain admins. (defaults to '')

        Returns:
            dict: Returns a confirmation that the user was deleted.

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

    # run command on an agent
    def run_command(self, node_id: str, command: str, runAsUser: int = 0) -> dict:

        data = {
            "action": "runcommands",
            "cmds": command,
            "nodeids": [f"node//{utils.b64_to_hex(node_id)}"],
            "runAsUser": runAsUser,
            "type": 1,
            "responseid": utils.gen_response_id(),
        }

        return self._send(data)
