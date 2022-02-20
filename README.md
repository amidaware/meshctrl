# MeshCtrl

## Usage Example

```py
from meshctrl-py import MeshCtrl

mesh_client = MeshCtrl(uri="wss://mesh.example.com", user="mesh username", token="mesh_login_token")
result = mesh_client.send_command(node_id="mesh_node_id", command="whoami")

print(result)
```
