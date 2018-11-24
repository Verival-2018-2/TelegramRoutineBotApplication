import sys
sys.path.insert(0, '../myroutinebot/')
from myroutinebot.handletask import HandleTask 
from myroutinebot.bot import Bot
import pytest


def test_task_condition():
    handletask = HandleTask()
    assert handletask.task_condition('teste', 'teste') == True

def test_check_msg_not_exists():
    handletask = HandleTask()
    assert handletask.check_msg_not_exists('test') == True

def test_condition_len_msg():
    handletask = HandleTask()
    assert handletask.condition_len_msg('2, test') == True