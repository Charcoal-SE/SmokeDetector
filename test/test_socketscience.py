from socketscience import SocketScience
import pytest


@pytest.mark.parameterize('content', [
    (".\n\u00022046b'\x82\xa8location\xabHenders/EC2\xa9timestamp\xcbA\xd6\xff\xb6~\xaay\xc3'\u0003",),
    (".\n\u00023786b'\x82\xa8location\xabHenders/EC2\xa9timestamp\xcbA\xd6\xff\xb5\x8e\x9c \x93'\u0003",)
])
def test_receive(content):
    def handle_ping(data):
        assert 'location' in data
        assert 'timestamp' in data

    SocketScience.register('ping', handle_ping)
    SocketScience.receive(content)
