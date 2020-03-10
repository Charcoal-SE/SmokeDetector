# coding=utf-8
# noinspection PyUnresolvedReferences
import chatcommunicate  # coverage
import chatcommands
from apigetpost import api_get_post
from parsing import to_protocol_relative
from classes._Post import Post
from globalvars import GlobalVars
from datahandling import _remove_pickle

import datetime
import os
import pytest
import regex
import types
import requests
if GlobalVars.on_windows:
    # noinspection PyPep8Naming
    from classes._Git_Windows import git
else:
    from sh.contrib import git

from fake import Fake
from unittest.mock import patch


def test_null():
    assert chatcommands.null() is None


def test_coffee():
    msg = Fake({"owner": {"name": "El'endia Starman"}})

    coffees = "\\*brews a cup of ({}) for ".format("|".join(chatcommands.COFFEES))
    assert regex.match(coffees + "@El'endiaStarman\\*", chatcommands.coffee(None, original_msg=msg))
    assert regex.match(coffees + "@angussidney\\*", chatcommands.coffee("angussidney"))


def test_tea():
    msg = Fake({"owner": {"name": "El'endia Starman"}})

    teas = "\\*brews a cup of ({}) tea for ".format("|".join(chatcommands.TEAS))
    assert regex.match(teas + "@El'endiaStarman\\*", chatcommands.tea(None, original_msg=msg))
    assert regex.match(teas + "@angussidney\\*", chatcommands.tea("angussidney"))


def test_lick():
    assert chatcommands.lick() == "*licks ice cream cone*"


def test_brownie():
    assert chatcommands.brownie() == "Brown!"


def test_wut():
    assert chatcommands.wut() == "Whaddya mean, 'wut'? Humans..."


def test_alive():
    assert chatcommands.alive() in chatcommands.ALIVE_MSG


def test_location():
    assert chatcommands.location() == GlobalVars.location


def test_version():
    assert chatcommands.version() == '{id} [{commit_name}]({repository}/commit/{commit_code})'.format(
        id=GlobalVars.location, commit_name=GlobalVars.commit_with_author_escaped,
        commit_code=GlobalVars.commit.id, repository=GlobalVars.bot_repository)


def test_bisect():
    chatcommunicate.parse_room_config("test/test_rooms.yml")
    msg = Fake({
        "owner": {
            "name": "ArtOfCode",
            "id": 121520,
            "is_moderator": True
        },
        "room": {
            "_client": {
                "host": "stackexchange.com"
            },
            "id": 11540
        },
        "content_source": None
    })
    # Testing for which watch/blacklist regex causes the problems
    # Test resulting in finding the \\L<city> issue
    # test_text = "<p>shiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiit!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!</p>\n"
    # test_text = ""
    # ('A post which hangs for minutes, but is NOT \\L<city>',
    # test_text = "<p>burhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhanburhan</p>\n"
    # ('Another post which hangs for minutes, but is NOT \\L<city>',
    # test_text = "<p>Eu quero ir pra morte ah vai foda-se ou não pode falar palavrão não é desse respeito que orientamos os outros a se gerar em esforços dedicados por fatos conhecidos pela equipe do espirito da lei nós precisamos oferecer uma orientação de objetivo com a superação da comunidade nós precisamos dar juízos dedicados á uma pessoa delicada é feio tirar dos outros frases malcriadas e ofensivas essa é a quebra da fração do bundo se não orientamos juízos fracionários em sensação com a superação negra do objetivo com o acordo da licença você pode perder sua capacidade de se tornar comunicado com a frequência conquistada por dever e você pode perder seu apoio da justiça nós precisamos apoiar aos outros um pensamento oferecido pela empresa é feio falar frases ofensivas e você pode receber uma denúncia para longe do planeta sem que ninguém use seus feitiços para te trazer pra terra e isso seria um prejuízo fatal que pode pagar multas críticas que te arranca do circuito do espirito e aí você vai perder sua forma de consideração de citação e não ter mais noção de viver aqui se você não ter uma força da união pensando no seu esforço e na sua nação de respeito citado pela lei você pode perder sua harmonia do bundo e ninguém mais vai falar com você e depois não adianta cagar nas calças pensando que sou boba tá bom uaaaaaaaaaaaaa ra ra ruiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiim na roupa floooooooooooooooooooooooooooooooooor quibe o churruuuuuuuuuuUuuuuuuuuuuuuuuuuus caio clock o vestiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiin geléia o naviuuuuuuuuuuuuuuuuuuuuu beijiiiiiiin uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu uuuuuuuuuuuuuuuuuuuuuuuuuu velma</p>\n"

    # ('Another post 2 which hangs for minutes, but is NOT \\L<city>',
    # test_text = "<p>0,000 5,000 10,00 15,00 20,00 25,00 30,00 35,00 40,00 45,00 50,00 55,00 60,00 65,00 70,00 75,00 80,00 85,00 90,00 95,00 100,0 105,0 110,0 115,0 120,0 125,0 130,0 135,0 140,0 145,0 150,0 155,0 160,0 165,0 170,0 175,0 180,0 185,0 190,0 195,0 200,0 205,0 210,0 215,0 220,0 225,0 230,0 235,0 240,0 245,0 250,0 255,0 260,0 265,0 270,0 275,0 280,0 285,0 290,0 295,0 300,0 305,0 310,0 315,0 320,0 325,0 330,0 335,0 340,0 345,0 350,0 355,0 360,0 365,0 370,0 375,0 380,0 385,0 390,0 395,0 400,0 405,0 410,0 415,0 420,0 425,0 430,0 435,0 440,0 445,0 450,0 455,0 460,0 465,0 470,0 475,0 480,0 485,0 490,0 495,0 500,0 505,0 510,0 515,0 520,0 525,0 530,0 535,0 540,0 545,0 550,0 555,0 560,0 565,0 570,0 575,0 580,0 585,0 590,0 595,0 600,0 605,0 610,0 615,0 620,0 625,0 630,0 635,0 640,0 645,0 650,0 655,0 660,0 665,0 670,0 675,0 680,0 685,0 690,0 695,0 700,0 705,0 710,0 715,0 720,0 725,0 730,0 735,0 740,0 745,0 750,0 755,0 760,0 765,0 770,0 775,0 780,0 785,0 790,0 795,0 800,0 805,0 810,0 815,0 820,0 825,0 830,0 835,0 840,0 845,0 850,0 855,0 860,0 865,0 870,0 875,0 880,0 885,0 890,0 895,0 900,0 905,0 910,0 915,0 920,0 925,0 930,0 935,0 940,0 945,0 950,0 955,0 960,0 965,0 970,0 975,0 980,0 985,0 990,0 995,0 100 100 101 101 102 102 103 103 104 104 105 105 106 106 107 107 108 108 109 109 110 110 111 111 112 112 113 113 114 114 115 115 116 116 117 117 118 118 119 119 120 120 121 121 122 122 123 123 124 124 125 125 126 126 127 127 128 128 129 129 130 130 131 131 132 132 133 133 134 134 135 135 136 136 137 137 138 138 139 139 140 140 141 141 142 142 143 143 144 144 145 145 146 146 147 147 148 148 149 149 150 150 151 151 152 152 153 153 154 154 155 155 156 156 157 157 158 158 159 159 160 160 161 161 162 162 163 163 164 164 165 165 166 166 167 167 168 168 169 169 170 170 171 171 172 172 173 173 174 174 175 175 176 176 177 177 178 178 179 179 180 180 181 181 182 182 183 183 184 184 185 185 186 186 187 187 188 188 189 189 190 190 191 191 192 192 193 193 194 194 195 195 196 196 197 197 198 198 199 199 200 200 201 201 202 202 203 203 204 204 205 205 206 206 207 207 208 208 209 209 210 210 211 211 212 212 213 213 214 214 215 215 216 216 217 217 218 218 219 219 220 220 221 221 222 222 223 223 224 224 225 225 226 226 227 227 228 228 229 229 230 230 231 231 232 232 233 233 234 234 235 235 236 236 237 237 238 238 239 239 240 240 241 241 242 242 243 243 244 244 245 245 246 246 247 247 248 248 249 249 250 250 251 251 252 252 253 253 254 254 255 255 256 256 257 257 258 258 259 259 260 260 261 261 262 262 263 263 264 264 265 265 266 266 267 267 268 268 269 269 270 270 271 271 272 272 273 273 274 274 275 275 276 276 277 277 278 278 279 279 280 280 281 281 282 282 283 283 284 284 285 285 286 286 287 287 288 288 289 289 290 290 291 291 292 292 293 293 294 294 295 295 296 296 297 297 298 298 299 299 300 300 301 301 302 302 303 303 304 304 305 305 306 306 307 307 308 308 309 309 310 310 311 311 312 312 313 313 314 314 315 315 316 316 317 317 318 318 319 319 320 320 321 321 322 322 323 323 324 324 325 325 326 326 327 327 328 328 329 329 330 330 331 331 332 332 333 333 334 334 335 335 336 336 337 337 338 338 339 339 340 340 341 341 342 342 343 343 344 344 345 345 346 346 347 347 348 348 349 349 350 350 351 351 352 352 353 353 354 354 355 355 356 356 357 357 358 358 359 359 360 360 361 361 362 362 363 363 364 364 365 365 366 366 367 367 368 368 369 369 370 370 371 371 372 372 373 373 374 374 375 375 376 376 377 377 378 378 379 379 380 380 381 381 382 382 383 383 384 384 385 385 386 386 387 387 388 388 389 389 390 390 391 391 392 392 393 393 394 394 395 395 396 396 397 397 398 398 399 399 400 400 401 401 402 402 403 403 404 404 405 405 406 406 407 407 408 408 409 409 410 410 411 411 412 412 413 413 414 414 415</p>\n"

    # msg.content_source = "!!/bisect {}".format(test_text)
    # assert chatcommands.bisect(None, original_msg=msg) == r"{!r} is not caught by a blacklist or watchlist item.".format(test_text)
    msg.content_source = "!!/bisect :::essayssos.com:::"
    assert chatcommands.bisect(None, original_msg=msg) == r"Matched by `essayssos\.com` on [line 1 of watched_keywords.txt](https://github.com/{}/blob/{}/watched_keywords.txt#L1)".format(GlobalVars.bot_repo_slug, GlobalVars.commit.id)
    test_text = "OoOasdfghjklOoO"
    msg.content_source = "!!/bisect {}".format(test_text)
    # msg.content_source = "!!/bisect OoOasdfghjklOoO"
    # assert chatcommands.bisect(None, original_msg=msg) == r"'OoOasdfghjklOoO' is not caught by a blacklist or watchlist item."
    assert chatcommands.bisect(None, original_msg=msg) == r"{!r} is not caught by a blacklist or watchlist item.".format(test_text)


"""
@patch("chatcommands.datetime")
def test_hats(date):
    date.side_effect = datetime.datetime

    date.utcnow.return_value = datetime.datetime(2018, 12, 11, hour=23)
    assert chatcommands.hats() == "WE LOVE HATS! Winter Bash will begin in 0 days, 1 hour, 0 minutes, and 0 seconds."

    date.utcnow.return_value = datetime.datetime(2019, 1, 1, hour=23)
    assert chatcommands.hats() == "Winter Bash won't end for 0 days, 1 hour, 0 minutes, and 0 seconds. GO EARN SOME HATS!"
"""


def test_info():
    assert chatcommands.info() == "I'm " + GlobalVars.chatmessage_prefix +\
        " a bot that detects spam and offensive posts on the network and"\
        " posts alerts to chat."\
        " [A command list is available here](https://charcoal-se.org/smokey/Commands)."


def test_blame():
    msg1 = Fake({
        "_client": {
            "host": "stackexchange.com",
            "get_user": lambda id: Fake({"name": "J F", "id": id})
        },

        "room": {
            "get_current_user_ids": lambda: [161943]
        }
    })

    assert chatcommands.blame(original_msg=msg1) == "It's [J F](https://chat.stackexchange.com/users/161943)'s fault."

    msg2 = Fake({
        "_client": {
            "host": "stackexchange.com",
            "get_user": lambda id: Fake({"name": "J F", "id": id})
        }
    })

    assert chatcommands.blame2("\u200B\u200C\u2060\u200D\u180E\uFEFF\u2063", original_msg=msg2) == "It's [J F](https://chat.stackexchange.com/users/161943)'s fault."


def test_privileged():
    chatcommunicate.parse_room_config("test/test_rooms.yml")

    msg = Fake({
        "owner": {
            "name": "ArtOfCode",
            "id": 121520,
            "is_moderator": False
        },
        "room": {
            "_client": {
                "host": "stackexchange.com"
            },
            "id": 11540
        }
    })

    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."

    msg.owner.id = 2
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2573 " + GlobalVars.not_privileged_warning

    msg.owner.is_moderator = True
    assert chatcommands.amiprivileged(original_msg=msg) == "\u2713 You are a privileged user."


def test_deprecated_blacklist():
    assert chatcommands.blacklist("").startswith("The `!!/blacklist` command has been deprecated.")


@pytest.mark.skipif(GlobalVars.on_branch != "master", reason="avoid branch checkout")
def test_watch(monkeypatch):
    # XXX TODO: expand
    def wrap_watch(pattern, force=False):
        cmd = 'watch{0}'.format('-force' if force else '')
        msg = Fake({
            "_client": {
                "host": "stackexchange.com",
                "get_user": lambda id: Fake({"name": "J F", "id": id})
            },
            "owner": {"name": "ArtOfCode", "id": 121520},
            "room": {"id": 11540, "get_current_user_ids": lambda: [161943]},
            # Ouch, this is iffy
            # Prevent an error from deep inside do_blacklist
            "content_source": '!!/{0} {1}'.format(cmd, pattern)
        })
        msg.room._client = msg._client

        return chatcommands.watch(pattern, alias_used=cmd, original_msg=msg)

    # Prevent from attempting to check privileges with Metasmoke
    monkeypatch.setattr(GlobalVars, "code_privileged_users", [1, 161943])

    try:
        # Invalid regex
        resp = wrap_watch(r'?')
        assert "An invalid pattern was provided" in resp

        # This is one of the perpetually condemned spam domains, blacklisted forever
        resp = wrap_watch(r'israelbigmarket')
        assert "That pattern looks like it's already caught" in resp

        # The phone number here is the first one in this format in bad_keywords.txt
        resp = wrap_watch(r'[a-z_]*(?:1_*)?913[\W_]*608[\W_]*4584[a-z_]*')
        assert "Mostly non-latin" not in resp
        assert "Bad keyword in answer" in resp
        assert "Bad keyword in body" in resp

        # XXX TODO: figure out how to trigger duplicate entry separately
        monkeypatch.setattr("chatcommunicate.is_privileged", lambda *args: True)
        monkeypatch.setattr("gitmanager.GitManager.prepare_git_for_operation", lambda *args: (True, None))

        assert wrap_watch("trimfire", True).startswith("Already watched")

        monkeypatch.setattr("gitmanager.GitManager.add_to_blacklist", lambda *args, **kwargs: (True, "Hahaha"))
        assert wrap_watch("male enhancement", True) == "Hahaha"
    finally:
        git.checkout("master")


def test_approve(monkeypatch):
    msg = Fake({
        "_client": {
            "host": "stackexchange.com",
        },
        "id": 88888888,
        "owner": {"name": "ArtOfCode", "id": 121520},
        "room": {"id": 11540, "name": "Continuous Integration", "_client": None},
        "content_source": '!!/approve 8888',
    })
    msg.room._client = msg._client

    # Prevent from attempting to check privileges with Metasmoke
    monkeypatch.setattr(GlobalVars, "code_privileged_users", [])
    assert chatcommands.approve(8888, original_msg=msg).startswith("You need code privileges")

    monkeypatch.setattr(GlobalVars, "code_privileged_users", [('stackexchange.com', 121520)])
    with monkeypatch.context() as m:
        # Oh no GitHub is down
        original_get = requests.get
        m.setattr("requests.get", lambda *args, **kwargs: None)
        assert chatcommands.approve(8888, original_msg=msg) == "Cannot connect to GitHub API"
        m.setattr("requests.get", original_get)
    assert chatcommands.approve(2518, original_msg=msg)[:8] in {"PR #2518", "Cannot c"}


@patch("chatcommands.handle_spam")
def test_report(handle_spam):
    # Documentation: The process before scanning the post is identical regardless of alias_used.
    #   No need to supply alias_used to test that part.
    #   If no alias_used is supplied, it acts as if it's "scan"
    try:
        msg = Fake({
            "owner": {
                "name": "ArtOfCode",
                "id": 121520,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "name": "Charcoal HQ",
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            },
            "id": 1337
        })

        assert chatcommands.report("test", original_msg=msg, alias_used="report") == "Post 1: That does not look like a valid post URL."

        assert chatcommands.report("one two three four five plus-an-extra", original_msg=msg, alias_used="report") == (
            "To avoid SmokeDetector reporting posts too slowly, you can report at most 5 posts at a time. This is to avoid "
            "SmokeDetector's chat messages getting rate-limited too much, which would slow down reports."
        )

        # assert chatcommands.report('a a a a a "invalid"""', original_msg=msg) \
        #     .startswith("You cannot provide multiple custom report reasons.")

        assert chatcommands.report('https://stackoverflow.com/q/1', original_msg=msg) == \
            "Post 1: Could not find data for this post in the API. It may already have been deleted."

        # Valid post
        assert chatcommands.report('https://stackoverflow.com/a/1732454', original_msg=msg, alias_used="scan") == \
            "Post 1: This does not look like spam"
        assert chatcommands.report('https://stackoverflow.com/a/1732454 "~o.O~"', original_msg=msg, alias_used="report") is None

        _, call = handle_spam.call_args_list[-1]
        assert isinstance(call["post"], Post)
        assert call["reasons"] == ["Manually reported answer"]
        assert call["why"] == (
            "Post manually reported by user *ArtOfCode* in room *Charcoal HQ* with reason: *~o.O~*."
            "\n\nThis post would not have been caught otherwise."
        )

        # Bad post
        # This post is found in Sandbox Archive, so it will remain intact and is a reliable test post
        # backup: https://meta.stackexchange.com/a/228635
        test_post_url = "https://meta.stackexchange.com/a/209772"
        assert chatcommands.report(test_post_url, original_msg=msg, alias_used="scan") is None

        _, call = handle_spam.call_args_list[-1]
        assert isinstance(call["post"], Post)
        assert call["why"].startswith("Post manually scanned by user *ArtOfCode* in room *Charcoal HQ*.")

        # Now with report-direct
        GlobalVars.blacklisted_users.clear()
        GlobalVars.latest_questions.clear()
        assert chatcommands.report(test_post_url, original_msg=msg, alias_used="report-direct") is None
        _, call = handle_spam.call_args_list[-1]
        assert isinstance(call["post"], Post)
        assert call["why"].startswith(
            "Post manually reported by user *ArtOfCode* in room *Charcoal HQ*."
            "\n\nThis post would have also been caught for:"
        )

        # Don't re-report
        GlobalVars.latest_questions = [('stackoverflow.com', '1732454', 'RegEx match open tags except XHTML self-contained tags')]
        assert chatcommands.report('https://stackoverflow.com/a/1732454', original_msg=msg).startswith("Post 1: Already recently reported")

        # Can use report command multiple times in 30s if only one URL was used
        assert chatcommands.report('https://stackoverflow.com/q/1732348', original_msg=msg, alias_used="report") is None
    finally:
        GlobalVars.blacklisted_users.clear()
        GlobalVars.latest_questions.clear()


@patch("chatcommands.handle_spam")
def test_allspam(handle_spam):
    try:
        msg = Fake({
            "owner": {
                "name": "ArtOfCode",
                "id": 121520,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "name": "Charcoal HQ",
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            },
            "id": 1337
        })

        assert chatcommands.allspam("test", original_msg=msg) == "That doesn't look like a valid user URL."

        # If this code lasts long enough to fail, I'll be happy
        assert chatcommands.allspam("https://stackexchange.com/users/10000000000", original_msg=msg) == \
            "The specified user does not appear to exist."

        assert chatcommands.allspam("https://stackexchange.com/users/5869449", original_msg=msg) == (
            "The specified user has an abnormally high number of accounts. Please consider flagging for moderator "
            "attention, otherwise use !!/report on the user's posts individually."
        )

        assert chatcommands.allspam("https://stackexchange.com/users/11683", original_msg=msg) == (
            "The specified user's reputation is abnormally high. Please consider flagging for moderator attention, "
            "otherwise use !!/report on the posts individually."
        )

        assert chatcommands.allspam("https://stackoverflow.com/users/22656", original_msg=msg) == (
            "The specified user's reputation is abnormally high. Please consider flagging for moderator attention, "
            "otherwise use !!/report on the posts individually."
        )

        assert chatcommands.allspam("https://stackexchange.com/users/12108751", original_msg=msg) == \
            "The specified user hasn't posted anything."

        assert chatcommands.allspam("https://stackoverflow.com/users/8846458", original_msg=msg) == \
            "The specified user has no posts on this site."

        # This test is for users with <100rep but >15 posts
        # If this breaks in the future because the below user eventually gets 100 rep (highly unlikely), use the following
        # data.SE query to find a new target. Alternatively, get a sock to post 16 answers in the sandbox.
        # https://stackoverflow.com/users/7052649/vibin (look for low rep but >1rep users, 1rep users are usually suspended)
        assert chatcommands.allspam("https://stackoverflow.com/users/7052649", original_msg=msg) == (
            "The specified user has an abnormally high number of spam posts. Please consider flagging for moderator "
            "attention, otherwise use !!/report on the posts individually."
        )

        # Valid user for allspam command
        assert chatcommands.allspam("https://stackexchange.com/users/12108974", original_msg=msg) is None

        assert handle_spam.call_count == 1
        _, call = handle_spam.call_args_list[0]
        assert isinstance(call["post"], Post)
        assert call["reasons"] == ["Manually reported answer"]
        assert call["why"] == "User manually reported by *ArtOfCode* in room *Charcoal HQ*.\n"

        handle_spam.reset_mock()
        assert chatcommands.allspam("https://meta.stackexchange.com/users/373807", original_msg=msg) is None

        assert handle_spam.call_count == 1
        _, call = handle_spam.call_args_list[0]
        assert isinstance(call["post"], Post)
        assert call["reasons"] == ["Manually reported answer"]
        assert call["why"] == "User manually reported by *ArtOfCode* in room *Charcoal HQ*.\n"

    finally:
        GlobalVars.blacklisted_users.clear()


@pytest.mark.skipif(os.path.isfile("blacklistedUsers.p"), reason="shouldn't overwrite file")
def test_blacklisted_users():
    try:
        msg = Fake({
            "owner": {
                "name": "ArtOfCode",
                "id": 121520,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            },
            "id": 1337
        })

        # Format: !!/*blu profileurl
        assert chatcommands.isblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.addblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User blacklisted (`4622463` on `stackoverflow.com`)."
        # TODO: Edit command to check and not blacklist again, add test
        assert chatcommands.isblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User removed from blacklist (`4622463` on `stackoverflow.com`)."
        assert chatcommands.isblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmblu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not blacklisted."

        # Format: !!/*blu userid sitename
        assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
            "User is not blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.addblu("4622463 stackoverflow", original_msg=msg) == \
            "User blacklisted (`4622463` on `stackoverflow.com`)."
        # TODO: Add test here as well
        assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
            "User is blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmblu("4622463 stackoverflow", original_msg=msg) == \
            "User removed from blacklist (`4622463` on `stackoverflow.com`)."
        assert chatcommands.isblu("4622463 stackoverflow", original_msg=msg) == \
            "User is not blacklisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmblu("4622463 stackoverflow", original_msg=msg) == \
            "User is not blacklisted."

        # Invalid input
        assert chatcommands.addblu("https://meta.stackexchange.com/users", original_msg=msg) == \
            "Invalid format. Valid format: `!!/addblu profileurl` *or* `!!/addblu userid sitename`."
        assert chatcommands.rmblu("https://meta.stackexchange.com/", original_msg=msg) == \
            "Invalid format. Valid format: `!!/rmblu profileurl` *or* `!!/rmblu userid sitename`."
        assert chatcommands.isblu("msklkldsklaskd", original_msg=msg) == \
            "Invalid format. Valid format: `!!/isblu profileurl` *or* `!!/isblu userid sitename`."

        # Invalid sitename
        assert chatcommands.addblu("1 completelyfakesite", original_msg=msg) == \
            "Error: Could not find the given site."
        assert chatcommands.isblu("1 completelyfakesite", original_msg=msg) == \
            "Error: Could not find the given site."
        assert chatcommands.rmblu("1 completelyfakesite", original_msg=msg) == \
            "Error: Could not find the given site."
    finally:
        # Cleanup
        _remove_pickle("blacklistedUsers.p")


@pytest.mark.skipif(os.path.isfile("whitelistedUsers.p"), reason="shouldn't overwrite file")
def test_whitelisted_users():
    try:
        msg = Fake({
            "owner": {
                "name": "El'endia Starman",
                "id": 1,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            }
        })

        # Format: !!/*wlu profileurl
        assert chatcommands.iswlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.addwlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User whitelisted (`4622463` on `stackoverflow.com`)."
        # TODO: Add test here as well
        assert chatcommands.iswlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmwlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User removed from whitelist (`4622463` on `stackoverflow.com`)."
        assert chatcommands.iswlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmwlu("https://stackoverflow.com/users/4622463/angussidney", original_msg=msg) == \
            "User is not whitelisted."

        # Format: !!/*wlu userid sitename
        assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
            "User is not whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.addwlu("4622463 stackoverflow", original_msg=msg) == \
            "User whitelisted (`4622463` on `stackoverflow.com`)."
        # TODO: Add test here as well
        assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
            "User is whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmwlu("4622463 stackoverflow", original_msg=msg) == \
            "User removed from whitelist (`4622463` on `stackoverflow.com`)."
        assert chatcommands.iswlu("4622463 stackoverflow", original_msg=msg) == \
            "User is not whitelisted (`4622463` on `stackoverflow.com`)."
        assert chatcommands.rmwlu("4622463 stackoverflow", original_msg=msg) == \
            "User is not whitelisted."

        # Invalid input
        assert chatcommands.addwlu("https://meta.stackexchange.com/users", original_msg=msg) == \
            "Invalid format. Valid format: `!!/addwlu profileurl` *or* `!!/addwlu userid sitename`."
        assert chatcommands.rmwlu("https://meta.stackexchange.com/", original_msg=msg) == \
            "Invalid format. Valid format: `!!/rmwlu profileurl` *or* `!!/rmwlu userid sitename`."
        assert chatcommands.iswlu("msklkldsklaskd", original_msg=msg) == \
            "Invalid format. Valid format: `!!/iswlu profileurl` *or* `!!/iswlu userid sitename`."

        # Invalid sitename
        assert chatcommands.addwlu("1 completelyfakesite", original_msg=msg) == \
            "Error: Could not find the given site."
        assert chatcommands.iswlu("1 completelyfakesite", original_msg=msg) == \
            "Error: Could not find the given site."
    except:
        # Cleanup
        _remove_pickle("whitelistedUsers.p")


def test_metasmoke():
    msg = Fake({
        "owner": {
            "name": "ArtOfCode",
            "id": 121520,
            "is_moderator": False
        },
        "room": {
            "id": 11540,
            "_client": {
                "host": "stackexchange.com"
            }
        },
        "_client": {
            "host": "stackexchange.com"
        }
    })
    msg_source = "metasmoke is {}. Current failure count: {} " + "({id})".format(id=GlobalVars.location)

    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-up") == "metasmoke is now considered up."
    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-status") == msg_source.format("up", 0)
    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-down") == "metasmoke is now considered down."
    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-status") == msg_source.format("down", 999)
    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-up") == "metasmoke is now considered up."
    assert chatcommands.metasmoke(original_msg=msg, alias_used="ms-status") == msg_source.format("up", 0)


@pytest.mark.skipif(os.path.isfile("notifications.p"), reason="shouldn't overwrite file")
def test_notifications():
    try:
        msg1 = Fake({
            "owner": {
                "name": "El'endia Starman",
                "id": 1,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            }
        })

        msg2 = Fake({
            "owner": {
                "name": "angussidney",
                "id": 145827,
                "is_moderator": False
            },
            "room": {
                "id": 11540,
                "_client": {
                    "host": "stackexchange.com"
                }
            },
            "_client": {
                "host": "stackexchange.com"
            }
        })

        # User 1
        assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
            "You won't get notified for any sites in that room."
        assert chatcommands.willbenotified("11540", "gaming", original_msg=msg1) == \
            "No, you won't be notified for that site in that room."
        assert chatcommands.notify("11540", "gaming", None, original_msg=msg1) == \
            "You'll now get pings from me if I report a post on `gaming`, in room `11540` on `chat.stackexchange.com`"
        assert chatcommands.notify("11540", "codegolf.stackexchange.com", None, original_msg=msg1) == \
            "You'll now get pings from me if I report a post on `codegolf.stackexchange.com`, in room `11540` on " \
            "`chat.stackexchange.com`"
        assert chatcommands.willbenotified("11540", "gaming.stackexchange.com", original_msg=msg1) == \
            "Yes, you will be notified for that site in that room."
        assert chatcommands.willbenotified("11540", "codegolf", original_msg=msg1) == \
            "Yes, you will be notified for that site in that room."

        # User 2
        assert chatcommands.allnotificationsites("11540", original_msg=msg2) == \
            "You won't get notified for any sites in that room."
        assert chatcommands.willbenotified("11540", "raspberrypi", original_msg=msg2) == \
            "No, you won't be notified for that site in that room."
        assert chatcommands.notify("11540", "raspberrypi", None, original_msg=msg2) == \
            "You'll now get pings from me if I report a post on `raspberrypi`, in room `11540` on `chat.stackexchange.com`"
        assert chatcommands.notify("11540", "raspberrypi", None, original_msg=msg2) == \
            "That notification configuration is already registered."
        assert chatcommands.willbenotified("11540", "raspberrypi.stackexchange.com", original_msg=msg2) == \
            "Yes, you will be notified for that site in that room."

        # Check for no interaction
        assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
            "You will get notified for these sites:\r\ncodegolf.stackexchange.com, gaming.stackexchange.com"
        assert chatcommands.allnotificationsites("11540", original_msg=msg2) == \
            "You will get notified for these sites:\r\nraspberrypi.stackexchange.com"

        # Remove all notifications and check
        assert chatcommands.unnotify("11540", "gaming.stackexchange.com", original_msg=msg1) == \
            "I will no longer ping you if I report a post on `gaming.stackexchange.com`, in room `11540` on " \
            "`chat.stackexchange.com`"
        assert chatcommands.unnotify("11540", "codegolf", original_msg=msg1) == \
            "I will no longer ping you if I report a post on `codegolf`, in room `11540` on `chat.stackexchange.com`"
        assert chatcommands.unnotify("11540", "raspberrypi", original_msg=msg2) == \
            "I will no longer ping you if I report a post on `raspberrypi`, in room `11540` on `chat.stackexchange.com`"
        assert chatcommands.unnotify("11540", "raspberrypi", original_msg=msg2) == \
            "That configuration doesn't exist."
        assert chatcommands.allnotificationsites("11540", original_msg=msg1) == \
            "You won't get notified for any sites in that room."
        assert chatcommands.willbenotified("11540", "raspberrypi", original_msg=msg2) == \
            "No, you won't be notified for that site in that room."

        assert chatcommands.allnotificationsites("asdf", original_msg=msg1) == "Invalid input type given for an argument"
        assert chatcommands.notify("11540", "charcoalspam.stackexchange.com", None, original_msg=msg1) == \
            "The given SE site does not exist."

        assert chatcommands.notify("11540", "codegolf", "True", original_msg=msg1) == \
            "You'll now get pings from me if I report a post on `codegolf`, in room `11540` on `chat.stackexchange.com`"
        assert chatcommands.notify("11540", "codegolf", "False", original_msg=msg1) == \
            "That notification configuration is already registered."
    finally:
        # Cleanup
        _remove_pickle("notifications.p")


def test_inqueue():
    site = Fake({"keys": (lambda: ['1'])})

    class FakeQueue:
        def __getitem__(self, _):
            return site

        def __contains__(self, name):
            return name == "codegolf.stackexchange.com"

    chatcommands.GlobalVars.bodyfetcher = Fake({"queue": FakeQueue()})

    assert chatcommands.inqueue("https://codegolf.stackexchange.com/a/1") == "Can't check for answers."
    assert chatcommands.inqueue("https://stackoverflow.com/q/1") == "Not in queue."
    assert chatcommands.inqueue("https://codegolf.stackexchange.com/q/1") == "#1 in queue."
