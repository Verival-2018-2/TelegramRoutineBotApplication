import sys
sys.path.insert(0, '../myroutinebot/')
from myroutinebot.handletask import HandleTask 
import pytest

def test_task_condition():
    handletask = HandleTask()
    assert handletask.task_condition('teste', 'teste') == True