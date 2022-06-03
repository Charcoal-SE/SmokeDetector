# coding=utf-8
from parsing import *
from globalvars import GlobalVars
import pytest

test_data_inputs = []
with GlobalVars.local_git_repository_file_lock:
    with open("test/data_test_parsing.txt", "r", encoding="utf-8") as f:
        # noinspection PyRedeclaration
        test_data_inputs = f.readlines()

# Large inputs should go to that file.
# Only inputs should go there, not the parsing method and the expected output,
# because the input is always a string and `parse_method` and `expected` are not.


# noinspection PyMissingTypeHints
@pytest.mark.parametrize("input_data, parse_method, expected", [
    ('Testing * escaping of ] special [ characters', escape_markdown, r'Testing \* escaping of \] special \[ characters'),
    ('HTML &#39; unescaping&lt;', unescape_title, 'HTML \' unescaping<'),
    ('https://physics.stackexchange.com/users/7433/manishearth', get_user_from_url, ('7433', 'physics.stackexchange.com')),
    ('https://softwarerecs.stackexchange.com/users/46/undo', get_user_from_url, ('46', 'softwarerecs.stackexchange.com')),
    ('https://earthscience.stackexchange.com/users/20/hichris123', get_user_from_url, ('20', 'earthscience.stackexchange.com')),
    ('https://codegolf.stackexchange.com/users/9275/programfox', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('https://stackoverflow.com/users/1/jeff-atwood', get_user_from_url, ('1', 'stackoverflow.com')),
    ('https://mathoverflow.net/users/66/ben-webster', get_user_from_url, ('66', 'mathoverflow.net')),
    ('http://codegolf.stackexchange.com/u/9275', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('https://codegolf.stackexchange.com/u/9275/', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('http://codegolf.stackexchange.com/users/9275', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('https://codegolf.stackexchange.com/users/9275/', get_user_from_url, ('9275', 'codegolf.stackexchange.com')),
    ('//stackoverflow.com/users/1/jeff-atwood', get_user_from_url, ('1', 'stackoverflow.com')),
    (None, get_user_from_url, None),
    ('Some text without a URL in it', get_user_from_url, None),
    ('https://stackoverflow.com/users/0/test', get_user_from_list_command, ('0', 'stackoverflow.com')),
    ('https://codegolf.stackexchange.com/users/9275/programfox', get_user_from_list_command, ('9275', 'codegolf.stackexchange.com')),
    ('https://mathoverflow.net/users/66/ben-webster', get_user_from_list_command, ('66', 'mathoverflow.net')),
    ('1234 stackoverflow.com', get_user_from_list_command, ('1234', 'stackoverflow.com')),
    ('4321 communitybuilding.stackexchange.com', get_user_from_list_command, ('4321', 'communitybuilding.stackexchange.com')),
    ('1 stackoverflow', get_user_from_list_command, ('1', 'stackoverflow.com')),
    ('https://stackoverflow.com/questions/1/title-here', url_to_shortlink, 'https://stackoverflow.com/questions/1'),
    ('https://stackoverflow.com/questions/1/title-here/2#2', url_to_shortlink, 'https://stackoverflow.com/a/2'),
    ('https://writers.stackexchange.com/questions/1/%2f%2f', url_to_shortlink, 'https://writers.stackexchange.com/questions/1'),
    ('http://writers.stackexchange.com/questions/1/%2f%2f/2#2', url_to_shortlink, 'https://writers.stackexchange.com/a/2'),
    ('https://mathoverflow.net/q/1', url_to_shortlink, 'https://mathoverflow.net/questions/1'),
    ('http://stackoverflow.com/users/1234/abcd', user_url_to_shortlink, 'https://stackoverflow.com/users/1234'),
    ('http://stackexchange.com', to_protocol_relative, '//stackexchange.com'),
    ('https://stackexchange.com', to_protocol_relative, '//stackexchange.com'),
    ('//stackexchange.com', to_protocol_relative, '//stackexchange.com'),
    ('https://stackoverflow.com/questions/123456/hello-world#654321', fetch_post_id_and_site_from_url, ('654321', 'stackoverflow.com', 'answer')),
    # ('sd 2tpu', preprocess_shortcut_command, 'sd tpu tpu'),
    # ('sd - 3tpu fp', preprocess_shortcut_command, 'sd - tpu tpu tpu fp'),
    # ('sd 3- 2fp', preprocess_shortcut_command, 'sd - - - fp fp'),
    # ('sd tpu fp ignore delete', preprocess_shortcut_command, 'sd tpu fp ignore delete'),
    # ('sd 5-', preprocess_shortcut_command, 'sd - - - - -'),
    # ('sd 15-', preprocess_shortcut_command, 'sd - - - - - - - - - - - - - - -'),
    # ('sd  tpu', preprocess_shortcut_command, 'sd tpu'),
    # ('sd 2 tpu', preprocess_shortcut_command, 'sd tpu tpu'),
    # ('sd 10 tpu', preprocess_shortcut_command, 'sd tpu tpu tpu tpu tpu tpu tpu tpu tpu tpu'),
    # ('sd fp 3   tpu', preprocess_shortcut_command, 'sd fp tpu tpu tpu'),
    ('stackoverflow.com', get_api_sitename_from_url, 'stackoverflow'),
    ('http://gaming.stackexchange.com', get_api_sitename_from_url, 'gaming'),
    ('https://mathoverflow.net/', get_api_sitename_from_url, 'mathoverflow.net'),
    (test_data_inputs[0], fetch_post_id_and_site_from_msg_content, ('246651', 'meta.stackexchange.com', 'question')),
    (test_data_inputs[0], fetch_owner_url_from_msg_content, 'https://meta.stackexchange.com/users/279263/lisa-usher'),
    (test_data_inputs[0], fetch_title_from_msg_content, 'Best Weight Loss Tips For Fast Results'),
    (test_data_inputs[1], fetch_post_url_from_msg_content, 'https://stackoverflow.com/questions/0/test-test'),
    (test_data_inputs[1], fetch_post_id_and_site_from_msg_content, ('0', 'stackoverflow.com', 'question')),
    (test_data_inputs[1], fetch_owner_url_from_msg_content, 'https://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[1], fetch_title_from_msg_content, 'TEST TEST TEST ]]])))'),
    (test_data_inputs[2], fetch_post_url_from_msg_content, 'http://stackoverflow.com/questions/0/test-test/42#42'),
    (test_data_inputs[2], fetch_post_id_and_site_from_msg_content, ('42', 'stackoverflow.com', 'answer')),
    (test_data_inputs[2], fetch_owner_url_from_msg_content, 'http://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[3], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[3], fetch_owner_url_from_msg_content, 'https://stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[3], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[4], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[4], fetch_owner_url_from_msg_content, None),
    (test_data_inputs[4], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[5], fetch_post_id_and_site_from_msg_content, ('246651', 'meta.stackexchange.com', 'question')),
    (test_data_inputs[5], fetch_owner_url_from_msg_content, 'https://meta.stackexchange.com/users/279263/lisa-usher'),
    (test_data_inputs[5], fetch_title_from_msg_content, 'Best Weight Loss Tips For Fast Results'),
    (test_data_inputs[6], fetch_post_url_from_msg_content, 'https://stackoverflow.com/q/0'),
    (test_data_inputs[6], fetch_post_id_and_site_from_msg_content, ('0', 'stackoverflow.com', 'question')),
    (test_data_inputs[6], fetch_owner_url_from_msg_content, 'https://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[6], fetch_title_from_msg_content, 'TEST TEST TEST ]]])))'),
    (test_data_inputs[7], fetch_post_url_from_msg_content, 'https://stackoverflow.com/a/42'),
    (test_data_inputs[7], fetch_post_id_and_site_from_msg_content, ('42', 'stackoverflow.com', 'answer')),
    (test_data_inputs[7], fetch_owner_url_from_msg_content, 'https://stackoverflow.com/users/0/test-test'),
    (test_data_inputs[8], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[8], fetch_owner_url_from_msg_content, 'https://stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[8], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[9], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[9], fetch_owner_url_from_msg_content, None),
    (test_data_inputs[9], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[10], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[10], fetch_owner_url_from_msg_content, '//stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[10], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[11], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[11], fetch_owner_url_from_msg_content, '//stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[11], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[12], fetch_post_id_and_site_from_msg_content, ('458053', 'ru.stackoverflow.com', 'question')),
    (test_data_inputs[12], fetch_owner_url_from_msg_content, '//ru.stackoverflow.com/users/20555/ni55an'),
    (test_data_inputs[12], fetch_title_from_msg_content, '-----------------------------'),
    (test_data_inputs[13], fetch_post_id_and_site_from_msg_content, ('458053', 'ru.stackoverflow.com', 'question')),
    (test_data_inputs[13], fetch_owner_url_from_msg_content, '//ru.stackoverflow.com/users/20555/ni55an'),
    (test_data_inputs[13], fetch_title_from_msg_content, '-----------------------------'),
    (test_data_inputs[14], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[14], fetch_owner_url_from_msg_content, '//stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[14], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[15], fetch_post_id_and_site_from_msg_content, ('27954020', 'stackoverflow.com', 'question')),
    (test_data_inputs[15], fetch_owner_url_from_msg_content, '//stackoverflow.com/users/3754535/user3754535'),
    (test_data_inputs[15], fetch_title_from_msg_content, "Why I can't insert data in a model from a custom controller?"),
    (test_data_inputs[15], edited_message_after_postgone_command, "[ [SmokeDetector](https://github.com/Charcoal-SE/SmokeDetector) ] Manually reported question (batch report: post 2 out of 3): *(gone)* by [user3754535](//stackoverflow.com/users/3754535/user3754535) on `stackoverflow.com`"),
    (test_data_inputs[16], fetch_post_id_and_site_from_msg_content, ('230329', 'drupal.stackexchange.com', 'question')),
    (test_data_inputs[16], fetch_title_from_msg_content, 'spammy spammy title'),
    (test_data_inputs[16], fetch_owner_url_from_msg_content, '//drupal.stackexchange.com/u/73447')
])
def test_parsing(input_data, parse_method, expected):
    if isinstance(input_data, str):
        assert parse_method(input_data.strip()) == expected
    else:
        assert parse_method(input_data) == expected


# noinspection PyMissingTypeHints
def test_post_parse_errors():
    from classes import Post, PostParseError
    failure = None
    try:
        failure = Post()
        assert 'Post with no initializer did not fail.' == 'An exception should have been generated and caught.'
    except PostParseError:
        pass
    assert failure is None


@pytest.mark.parametrize('link, param', [
    ('stackoverflow.com', 'stackoverflow'),
    ('//stackoverflow.com', 'stackoverflow'),
    ('https://stackoverflow.com', 'stackoverflow'),
    ('https://stackoverflow.com/', 'stackoverflow'),
    ('//stackoverflow.com/questions/12345678', 'stackoverflow'),
    ('//stackoverflow.com/a/12345678', 'stackoverflow'),
    ('mathoverflow.net', 'mathoverflow.net'),
    ('superuser.com', 'superuser'),
    ('serverfault.com', 'serverfault'),
    ('askubuntu.com', 'askubuntu'),
    ('3dprinting.stackexchange.com', '3dprinting'),
    ('blender.stackexchange.com', 'blender'),
    ('//blender.stackexchange.com', 'blender'),
    ('https://blender.stackexchange.com', 'blender'),
    ('https://blender.stackexchange.com/', 'blender'),
    ('//blender.stackexchange.com/questions/123456', 'blender'),
    ('//blender.stackexchange.com/a/123456', 'blender'),
    ('meta.stackoverflow.com', 'meta.stackoverflow'),
    ('//meta.stackoverflow.com', 'meta.stackoverflow'),
    ('https://meta.stackoverflow.com', 'meta.stackoverflow'),
    ('https://meta.stackoverflow.com/', 'meta.stackoverflow'),
    ('//meta.stackoverflow.com/questions/12345678', 'meta.stackoverflow'),
    ('//meta.stackoverflow.com/a/12345678', 'meta.stackoverflow'),
    ('meta.mathoverflow.net', 'meta.mathoverflow.net'),
    ('meta.superuser.com', 'meta.superuser'),
    ('meta.serverfault.com', 'meta.serverfault'),
    ('meta.askubuntu.com', 'meta.askubuntu'),
    ('3dprinting.meta.stackexchange.com', '3dprinting.meta'),
    ('blender.meta.stackexchange.com', 'blender.meta'),
    ('meta.stackexchange.com', 'meta'),
    ('ja.stackoverflow.com', 'ja.stackoverflow'),
    ('meta.ja.stackoverflow.com', 'meta.ja.stackoverflow')
])
def test_api_parameter_from_link(link, param):
    assert api_parameter_from_link(link) == param
