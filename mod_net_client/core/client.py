"""Core client for interacting with the module registry."""

from substrateinterface import SubstrateInterface


class ModNetClient:
    """Client for interacting with the Mod-Net module registry."""

    def __init__(
        self,
        substrate_url: str,
        *,
        ipfs_api_url: str | None = None,
        ipfs_gateway_url: str | None = None,
    ) -> None:
        """Initialize the ModNet client.

        Args:
            substrate_url: URL of the substrate node
            ipfs_api_url: Optional IPFS API URL (default: http://localhost:5001)
            ipfs_gateway_url: Optional IPFS gateway URL (default: http://localhost:8080)
        """
        self.substrate = SubstrateInterface(url=substrate_url)
        self.ipfs_api_url = ipfs_api_url or "http://localhost:5001"
        self.ipfs_gateway_url = ipfs_gateway_url or "http://localhost:8080"

    def health_check(self) -> bool:
        """Check if the client can connect to the substrate node.

        Returns:
            bool: True if connection is healthy
        """
        try:
            self.substrate.get_chain_head()
            return True
        except Exception:
            return False
