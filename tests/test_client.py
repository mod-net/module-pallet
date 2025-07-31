"""Tests for the ModNet client."""

from unittest.mock import MagicMock, patch

from mod_net_client.core.client import ModNetClient


def test_client_initialization() -> None:
    """Test client initialization with default values."""
    client = ModNetClient("ws://localhost:9944")
    assert client.ipfs_api_url == "http://localhost:5001"
    assert client.ipfs_gateway_url == "http://localhost:8080"


def test_client_custom_ipfs_urls() -> None:
    """Test client initialization with custom IPFS URLs."""
    client = ModNetClient(
        "ws://localhost:9944",
        ipfs_api_url="http://custom:5001",
        ipfs_gateway_url="http://custom:8080",
    )
    assert client.ipfs_api_url == "http://custom:5001"
    assert client.ipfs_gateway_url == "http://custom:8080"


@patch("substrate_interface.SubstrateInterface")
def test_health_check_success(mock_substrate: MagicMock) -> None:
    """Test successful health check."""
    mock_substrate.return_value.get_chain_head.return_value = "0x1234"
    client = ModNetClient("ws://localhost:9944")
    assert client.health_check() is True


@patch("substrate_interface.SubstrateInterface")
def test_health_check_failure(mock_substrate: MagicMock) -> None:
    """Test failed health check."""
    mock_substrate.return_value.get_chain_head.side_effect = Exception(
        "Connection failed"
    )
    client = ModNetClient("ws://localhost:9944")
    assert client.health_check() is False
