import json

import pytest

from sidecar.dictionary_bias import PhraseBias, compile_bias, recognition_terms, restore_case


def test_only_case_of_complete_recognized_terms_is_restored():
    assert restore_case('I use phonon.', ['Phonon']) == 'I use Phonon.'
    assert restore_case('Put my phone on the table.', ['Phonon']) == 'Put my phone on the table.'
    assert restore_case('A phonon and two phonons.', ['Phonon']) == 'A Phonon and two phonons.'


def test_prefixes_reset_after_unrelated_tokens_and_support_overlaps():
    bias = PhraseBias([[1, 2, 3], [2, 4]], strength=1.5)
    first = bias.advance(0, 1)
    assert bias.bonuses(first)[2] == 1.5
    second = bias.advance(first, 2)
    assert bias.bonuses(second)[3] == 1.5
    assert bias.bonuses(second)[4] == 1.5
    assert bias.advance(second, 99) == 0
    assert bias.bonuses(0) == {1: 0.375, 2: 0.375}


def test_duplicate_terms_do_not_increase_boost():
    single = PhraseBias([[1, 2]])
    repeated = PhraseBias([[1, 2]] * 50)
    assert repeated.bonuses(0) == single.bonuses(0)
    assert repeated.bonuses(repeated.advance(0, 1)) == single.bonuses(single.advance(0, 1))


def test_bonus_cannot_overrule_an_arbitrarily_stronger_prediction():
    bias = PhraseBias([[1, 2]], strength=1.5)
    state = bias.advance(0, 1)
    logits = {2: -5, 3: 0}
    scores = {token: value + bias.bonuses(state).get(token, 0) for token, value in logits.items()}
    assert max(scores, key=scores.get) == 3


def test_setting_and_dictionary_edits_take_effect_on_next_read(tmp_path):
    assert recognition_terms(tmp_path) == []
    dictionary = tmp_path / 'dictionary.json'
    dictionary.write_text(json.dumps({'entries': [
        {'phrase': 'Phonon'}, {'phrase': 'Phonon'},
        {'phrase': 'sign off', 'replacement': 'My entire signature'},
    ]}))
    assert recognition_terms(tmp_path) == ['Phonon']
    settings = tmp_path / 'settings.json'
    settings.write_text('{"dictionary_recognition":false}')
    assert recognition_terms(tmp_path) == []
    settings.write_text('{"dictionary_recognition":true}')
    dictionary.write_text('{"entries":[{"phrase":"Another name"}]}')
    assert recognition_terms(tmp_path) == ['Another name']


class Tokenizer:
    def encode(self, word, out_type):
        return [1, 2] if out_type is int else ['a', 'b']

    def unk_id(self):
        return 0


def test_tokens_must_match_the_models_vocabulary():
    with pytest.raises(ValueError, match='cannot map'):
        compile_bias(['term'], Tokenizer(), ['<unk>', 'x', 'y'])
    assert compile_bias(['term'], Tokenizer(), ['<unk>', 'a', 'b']) is not None
    assert compile_bias([], Tokenizer(), ['<unk>', 'a', 'b']) is None
    assert compile_bias(['term'], Tokenizer(), ['<unk>', 'a', 'b'], strength=0) is None


def test_unrecognized_characters_fail_instead_of_boosting_unknown():
    class Unknown(Tokenizer):
        def encode(self, word, out_type):
            return [0] if out_type is int else ['<unk>']
    with pytest.raises(ValueError, match='cannot map'):
        compile_bias(['unrecognized'], Unknown(), ['<unk>', 'a', 'b'])


def test_invalid_strength_rejected():
    with pytest.raises(ValueError):
        PhraseBias([[1]], strength=10)
