# coding=utf-8
# noinspection PyUnresolvedReferences
import phone_numbers
import pytest


@pytest.mark.parametrize("text, expected_unprocessed, expected_normalized, expected_deobfuscated", [
    ("1234567890", {"1234567890"}, {'1234567890'}, set()),
    ("1234S67890", {"1234S67890"}, {"123467890"}, {"1234567890"}),
    ("1 234S67890", {"1 234S67890", "234S67890"}, {"123467890", "23467890"}, {"1234567890", "234567890"}),
])
def test_get_all_candidates(text, expected_unprocessed, expected_normalized, expected_deobfuscated):
    print('text:', text, ':: exp_unprocessed:', expected_unprocessed, ':: exp_normalized:', expected_normalized, ':: exp_deobfuscated:', expected_deobfuscated)
    unprocessed, normalized, deobfuscated = phone_numbers.get_all_candidates(text)
    print('text:', text, '::     unprocessed:', unprocessed, '::     normalized:', normalized, '::      deobfuscated:', deobfuscated)
    assert unprocessed == expected_unprocessed
    assert normalized == expected_normalized
    assert deobfuscated == expected_deobfuscated


@pytest.mark.parametrize("numlist, processed_in, normalized_in, expected_full_list, expected_processed, expected_normalized", [
    (["1234567890"], None, None, {'1234567890': ('1234567890', {'1234567890'})}, {'1234567890'}, {'1234567890'}),
    (["1234S67890"], None, None, {'1234S67890': ('1234S67890', {"123467890", "1234567890"})}, {'1234S67890'}, {"123467890", "1234567890"}),  # De-obfuscate "S" -> "5"
    (["1 234S67890"], None, None, {'1 234S67890': ('1 234S67890', {"123467890", "1234567890"})}, {'1 234S67890'}, {"123467890", "1234567890"}),  # De-obfuscate "S" -> "5"
    (["1-234-567-8900"], None, None, {'1-234-567-8900': ('1-234-567-8900', {'12345678900', '2345678900'})}, {'1-234-567-8900'}, {'12345678900', '2345678900'}),  # North American: remove 1
    (["234-567-8900"], None, None, {'234-567-8900': ('234-567-8900', {'12345678900', '2345678900'})}, {'234-567-8900'}, {'12345678900', '2345678900'}),  # North American: add 1
    (["234-567-8900(?#Some comment)"], None, None, {'234-567-8900(?#Some comment)': ('234-567-8900', {'12345678900', '2345678900'})}, {'234-567-8900'}, {'12345678900', '2345678900'}),  # North American: add 1; remove comment
    (["234-567-8900(?#NO NorAm)"], None, None, {'234-567-8900(?#NO NorAm)': ('234-567-8900', {'2345678900'})}, {'234-567-8900'}, {'2345678900'}),  # Force not North American
    (["2345678-900(?#IS NorAm)"], None, None, {'2345678-900(?#IS NorAm)': ('2345678-900', {'12345678900', '2345678900'})}, {'2345678-900'}, {'12345678900', '2345678900'}),  # Force IS North American
])
def test_process_numlist(numlist, processed_in, normalized_in, expected_full_list, expected_processed, expected_normalized):
    print('numlist:', numlist, ':: exp_full_list:', expected_full_list, ':: exp_processed:', expected_processed, ':: exp_normalized:', expected_normalized)
    full_list, processed, normalized = phone_numbers.process_numlist(numlist, processed_in, normalized_in)
    print('numlist:', numlist, '::     full_list:', full_list, '::     processed:', processed, '::      normalized:', normalized)
    assert full_list == expected_full_list
    assert processed == expected_processed
    assert normalized == expected_normalized
