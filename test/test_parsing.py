from parsing import *
import pytest

test_data_inputs = []
with open("test/data_test_parsing.txt", "r") as f:
    test_data_inputs = f.readlines()

# Large inputs should go to that file.
# Only inputs should go there, not the parsing method and the expected output,
# because the input is always a string and `parse_method` and `expected` are not.


@pytest.mark.parametrize("input_data, parse_method, expected", [
    ('Testing * escaping of ] special [ characters', escape_special_chars_in_title, 'Testing \* escaping of \] special \[ characters'),
    ('HTML &#39; unescaping&lt;', unescape_title, 'HTML \' unescaping<'),
    ('http://physics.stackexchange.com/users/7433/manishearth', get_user_from_url, ('7433', 'physics.stackexchange.com')),
    ('http://softwarerecs.stackexchange.com/users/46/undo', get_user_from_url, ('46', 'softwarerecs.stackexchange.com')),
    ('http://earthscience.stackexchange.com/users/20/hichris123', get_user_from_url, ('20', 'earthscience.stackexchange.com')),
    ('http://codegolf.stackexchange.com/users/9275/programfox', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('http://stackoverflow.com/users/1/jeff-atwood', get_user_from_url, ('1', 'stackoverflow.com')),
    ('http://mathoverflow.net/users/66/ben-webster', get_user_from_url, ('66', 'mathoverflow.net')),
    ('!!/addblu http://stackoverflow.com/users/0/test', get_user_from_list_command, ('0', 'stackoverflow.com')),
    ('!!/rmblu http://stackoverflow.com/users/0/test', get_user_from_list_command, ('0', 'stackoverflow.com')),
    ('!!/addwlu http://stackoverflow.com/users/0/test', get_user_from_list_command, ('0', 'stackoverflow.com')),
    ('!!/rmwlu http://stackoverflow.com/users/0/test', get_user_from_list_command, ('0', 'stackoverflow.com')),
    ('!!/addwlu http://codegolf.stackexchange.com/users/9275/programfox', get_user_from_list_command, ('9275', 'codegolf.stackexchange.com')),
    ('!!/addwlu http://mathoverflow.net/users/66/ben-webster', get_user_from_list_command, ('66', 'mathoverflow.net')),
    ('!!/rmblu 1234 stackoverflow.com', get_user_from_list_command, ('1234', 'stackoverflow.com')),
    ('!!/rmwlu 4321 communitybuilding.stackexchange.com', get_user_from_list_command, ('4321', 'communitybuilding.stackexchange.com')),
    ('!!/addblu 1 stackoverflow', get_user_from_list_command, ('1', 'stackoverflow.com')),
    ('http://stackoverflow.com/questions/1/title-here', url_to_shortlink, 'http://stackoverflow.com/q/1'),
    ('http://stackoverflow.com/questions/1/title-here/2#2', url_to_shortlink, 'http://stackoverflow.com/a/2'),
    ('http://writers.stackexchange.com/questions/1/%2f%2f', url_to_shortlink, 'http://writers.stackexchange.com/q/1'),
    ('http://writers.stackexchange.com/questions/1/%2f%2f/2#2', url_to_shortlink, 'http://writers.stackexchange.com/a/2'),
    ('http://mathoverflow.net/q/1', url_to_shortlink, 'http://mathoverflow.net/q/1'),
    ('sd 2tpu', preprocess_shortcut_command, 'sd tpu tpu'),
    ('sd - 3tpu fp', preprocess_shortcut_command, 'sd - tpu tpu tpu fp'),
    ('sd 3- 2fp', preprocess_shortcut_command, 'sd - - - fp fp'),
    ('sd tpu fp ignore delete', preprocess_shortcut_command, 'sd tpu fp ignore delete'),
    ('sd 5-', preprocess_shortcut_command, 'sd - - - - -'),
    ('sd  tpu', preprocess_shortcut_command, 'sd tpu'),
    (test_data_inputs[0], fetch_post_id_and_site_from_msg_content, ('246651', 'meta.stackexchange.com', 'question')),
    (test_data_inputs[0], fetch_owner_url_from_msg_content, 'http://meta.stackexchange.com/users/279263/lisa-usher'),
    (test_data_inputs[0], fetch_title_from_msg_content, 'Best Weight Loss Tips For Fast Results'),
    (test_data_inputs[1], fetch_post_url_from_msg_content, 'http://stackoverflow.com/questions/0/test-test'),
    (test_data_inputs[1], fetch_post_id_and_site_from_msg_content, ('0', 'stackoverflow.com', 'question')),
    (test_data_inputs[1], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[1], fetch_title_from_msg_content, 'TEST TEST TEST ]]])))'),
    (test_data_inputs[2], fetch_post_url_from_msg_content, 'http://stackoverflow.com/questions/0/test-test/42#42'),
    (test_data_inputs[2], fetch_post_id_and_site_from_msg_content, ('42', 'stackoverflow.com', 'answer')),
    (test_data_inputs[2], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[3], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[3], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[3], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[4], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[4], fetch_owner_url_from_msg_content, None),
    (test_data_inputs[4], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[5], fetch_post_id_and_site_from_msg_content, ('246651', 'meta.stackexchange.com', 'question')),
    (test_data_inputs[5], fetch_owner_url_from_msg_content, 'http://meta.stackexchange.com/users/279263/lisa-usher'),
    (test_data_inputs[5], fetch_title_from_msg_content, 'Best Weight Loss Tips For Fast Results'),
    (test_data_inputs[6], fetch_post_url_from_msg_content, 'http://stackoverflow.com/q/0'),
    (test_data_inputs[6], fetch_post_id_and_site_from_msg_content, ('0', 'stackoverflow.com', 'question')),
    (test_data_inputs[6], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[6], fetch_title_from_msg_content, 'TEST TEST TEST ]]])))'),
    (test_data_inputs[7], fetch_post_url_from_msg_content, 'http://stackoverflow.com/a/42'),
    (test_data_inputs[7], fetch_post_id_and_site_from_msg_content, ('42', 'stackoverflow.com', 'answer')),
    (test_data_inputs[7], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[8], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[8], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[8], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[9], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[9], fetch_owner_url_from_msg_content, None),
    (test_data_inputs[9], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?")
])
def test_parsing(input_data, parse_method, expected):
    assert parse_method(input_data.strip()) == expected
