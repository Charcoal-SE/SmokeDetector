from parsing import *
import pytest

test_data_inputs = []
with open("test/data_test_parsing.txt", "r") as f:
    test_data_inputs = f.readlines()

# Large inputs should go to that file.
# Only inputs should go there, not the parsing method and the expected output,
# because the input is always a string and `parse_method` and `expected` are not.

@pytest.mark.parametrize("input_data, parse_method, expected", [
    ('http://physics.stackexchange.com/users/7433/manishearth', get_user_from_url, ('7433', 'physics.stackexchange.com')),
    ('http://softwarerecs.stackexchange.com/users/46/undo', get_user_from_url, ('46', 'softwarerecs.stackexchange.com')),
    ('http://earthscience.stackexchange.com/users/20/hichris123', get_user_from_url, ('20', 'earthscience.stackexchange.com')),
    ('http://codegolf.stackexchange.com/users/9275/programfox', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('http://stackoverflow.com/users/1/jeff-atwood', get_user_from_url, ('1', 'stackoverflow.com')),
    ('http://mathoverflow.net/users/66/ben-webster', get_user_from_url, ('66', 'mathoverflow.net')),
    (test_data_inputs[0], fetch_post_id_and_site_from_msg_content, ('246651', 'meta.stackexchange.com')),
    (test_data_inputs[0], fetch_owner_url_from_msg_content, 'http://meta.stackexchange.com/users/279263/lisa-usher'),
    (test_data_inputs[0], fetch_title_from_msg_content, 'Best Weight Loss Tips For Fast Results'),
    (test_data_inputs[1], fetch_post_id_and_site_from_msg_content, ('0', 'stackoverflow.com')),
    (test_data_inputs[1], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[1], fetch_title_from_msg_content, 'TEST TEST TEST ]]])))'),
    (test_data_inputs[2], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com')),
    (test_data_inputs[2], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[2], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?")
])

def test_parsing(input_data, parse_method, expected):
    assert parse_method(input_data) == expected
