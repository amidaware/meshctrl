import json
import uuid
import websockets

import meshctrl

class MeshCtrl():

    def __init__(self, uri: str, token: str, user: str):
        self.uri = uri
        self.user = user
        self.token = token

    async def _websocket_call(self, data: dict) -> dict:
        token = meshctrl.utils.get_auth_token(self.user, self.token)

        uri = f"{uri}/control.ashx?auth={token}"

        async with websockets.connect(uri) as websocket:
            
            responseId = uuid.uuid4()
            data["responseId"] = responseId

            await websocket.send(
                json.dumps(data)
            )

            async for message in websocket:
                response = json.loads(message)

                if response["responseId"] == responseId:
                    return response

    # pulls a list of groups in MeshCentral
    def get_mesh_groups(self) -> dict:
        data = {
            "action": "meshes"
        }

        return self._websocket_call(json.dumps(data))


    # created a group with the specified name
    def create_mesh_group(self, name: str) -> dict:
        data =  {
            "action": "createmesh",
            "meshname": name,
            "meshtype": 2,
        }

        return self._websocket_call(json.dumps(data))

    # run command on an agent
    def run_command(self, node_id: str, command: str, runAsUser: int = 0) -> dict:
        data =                     {
            "action": "runcommands",
            "cmds": command,
            "nodeids": [f"node//{meshctrl.utils.b64_to_hex(node_id)}"],
            "runAsUser": runAsUser,
            "type": 1,
        }

        return self._websocket_call(json.dumps(data))
