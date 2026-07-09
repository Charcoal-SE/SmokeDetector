# coding=utf-8
import pytest

from socketscience import SocketScience


@pytest.mark.parametrize('content', [
    ".\n\x023359gaRwaW5ngqhsb2NhdGlvbqtIZW5kZXJzL0VDMql0aW1lc3RhbXDOWseSrg==\x03"
])
def test_receive(content):
    def handle_ping(data):
        assert 'location' in data
        assert 'timestamp' in data

    SocketScience.register('ping', handle_ping)
    SocketScience.receive(content)
