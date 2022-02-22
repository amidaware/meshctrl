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
