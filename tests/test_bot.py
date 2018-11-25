import sys, os
myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, myPath + '/../myroutinebot/')
from myroutinebot.handletask import HandleTask 
from myroutinebot.bot import Bot
import pytest


def test_get_url():
    bot = Bot()
    assert isinstance(bot.get_url(bot.URL), str)
