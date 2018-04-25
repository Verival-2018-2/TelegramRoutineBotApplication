#!/usr/bin/env python3

import json
import requests
import time
import urllib
from pathlib import Path
from dateutil import parser
import sqlalchemy
import db
from db import Task
import os
import json
import requests


class Bot():
    def __init__(self):
        self.TOKEN = self.get_infos_file("/token_my_routinebot.txt", False)
        self.URL = "https://api.telegram.org/bot{}/".format(self.TOKEN)
        self.HELP = """
                    /new NOME
                    /todo ID
                    /doing ID
                    /done ID
                    /delete ID
                    /list
                    /rename ID NOME
                    /dependson ID ID...
                    /duplicate ID
                    /priority ID PRIORITY{low, medium, high}
                    /help
                    """

    def get_infos_file(self, input_file, set_password=False):
        home = str(Path.home())
        # input_file = "/token_my_routinebot.txt"
        with open(home + input_file) as infile:
            if set_password == True:
                lines = infile.readline()[1:]
            lines = infile.readline()
        info = ""
        for line in lines:
            info += line
        info = info.rstrip('\n')
        return info

    def make_github_issue(self, title, body=None):
        '''Create an issue on github.com using the given parameters.'''
        # Our url to create issues via POST
        url = 'https://api.github.com/repos/TecProg-20181/my_routinebot/issues'
        # Create an authenticated session to create the issue
        session = requests.Session()
        session.auth = (get_infos_file("/username_git.txt", False),
                        get_infos_file("/username_git.txt", True))
        # Create our issue
        issue = {'title': title,
                 'body': body}
        # Add the issue to our repository
        r = session.post(url, json.dumps(issue))
        if r.status_code == 201:
            print ('Successfully created Issue {0:s}'.format(title))
        else:
            print ('Could not create Issue {0:s}'.format(title))
            print ('Response:', r.content)

    def get_url(self, url):
        response = requests.get(url)
        content = response.content.decode("utf8")
        return content

    def get_json_from_url(self, url):
        content = self.get_url(url)
        js = json.loads(content)
        return js

    def get_updates(self, offset=None):
        url = self.URL + "getUpdates?timeout=100"
        if offset:
            url += "&offset={}".format(offset)
        js = self.get_json_from_url(url)
        return js

    def send_message(self, text, chat_id, reply_markup=None):
        text = urllib.parse.quote_plus(text)
        url = self.URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown"\
                         .format(text, chat_id)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        self.get_url(url)

    def get_last_update_id(self, updates):
        update_ids = []
        for update in updates["result"]:
            update_ids.append(int(update["update_id"]))
        return max(update_ids)

    def deps_text(self, task, chat, preceed=''):
        text = ''

        for i in range(len(task.dependencies.split(',')[:-1])):
            line = preceed
            query = db.session.query(Task)\
                                     .filter_by(id=int(task.dependencies\
                                                .split(',')[:-1][i]),\
                                                chat=chat)
            dep = query.one()

            icon = '\U0001F195'
            if dep.status == 'DOING':
                icon = '\U000023FA'
            elif dep.status == 'DONE':
                icon = '\U00002611'

            if i + 1 == len(task.dependencies.split(',')[:-1]):
                line += '└── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
                line += self.deps_text(dep, chat, preceed + '    ')
            else:
                line += '├── [[{}]] {} {}\n'.format(dep.id, icon, dep.name)
                line += self.deps_text(dep, self.chat, self.preceed + '│   ')

            text += line
        return text

    def set_command_text(self, command):
        if command == '/new':
            text = 'New task *TODO* [[{}]] {}'
        elif command == '/rename':
            text = "You want to modify task {},\\\
                    but you didn't provide any new text"
        elif command == '/duplicate':
            text = 'New task *TODO* [[{}]] {}'
        elif command == '/delete':
            text = 'Task [[{}]] deleted'
        elif command == '/todo':
            text = '*TODO* task [[{}]] {}'
        elif command == '/doing':
            text = '*DOING* task [[{}]] {}'
        elif command == '/done':
            text = '*DONE* task [[{}]] {}'
        elif command == '/dependson':
            text = 'Task {} dependencies up to date'
        elif command == '/priority':
            text = '*Task {}* priority has priority *{}*'
        elif command == '/start':
            text = 'Welcome! Here is a list of things you can do.'
        elif command == '/help':
            text = 'Here is a list of things you can do.'
        # elif command == '/list' #fazer método para setar list
            # text = 'metodo para lista'
        return text

    def check_msg_not_exists(self, msg):
        if not msg.isdigit():
            return True

    def msg_no_task(self, chat):
        self.send_message("You must inform the task id", chat)

    def new_task(self, command, msg, chat):
        task = Task(chat=chat, name=msg, status='TODO',
                    dependencies='', parents='', priority='')
        db.session.add(task)
        db.session.commit()
        self.send_message(self.set_command_text(command)\
                    .format(task.id, task.name), chat)
        # self.make_github_issue(task.name, 'Task of ID:[[{}]].\n\\\
                                    #   Name of task:{}\n'\
                                    #   .format(task.id, task.name))

    def rename(self, command, msg, chat):
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id,
                                                     chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return

            if text == '':
                self.send_message("You want to modify task {},\\\
                              but you didn't provide any new text"\
                              .format(task_id), chat)
                return

            old_text = task.name
            task.name = text
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task_id, old_text, text), chat)

    def duplicate(self, command, msg, chat):
        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x".format(task_id),
                                                                  self.chat)
                return

            dtask = Task(chat=task.chat, name=task.name, status=task.status,
                         dependencies=task.dependencies, parents=task.parents,
                         priority=task.priority, duedate=task.duedate)
            db.session.add(dtask)

            for t in task.dependencies.split(',')[:-1]:
                qy = db.session.query(Task).filter_by(id=int(t), chat=self.chat)
                t = qy.one()
                t.parents += '{},'.format(dtask.id)
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                        .format(dtask.id, dtask.name), chat)


    def delete(self, command, msg, chat):
        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task)\
                                     .filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return
            for t in task.dependencies.split(',')[:-1]:
                qy = db.session.query(Task)\
                                      .filter_by(id=int(t), chat=chat)
                t = qy.one()
                t.parents = t.parents\
                            .replace('{},'.format(task.id), '')
            db.session.delete(task)
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task_id), chat)
    def todo(self, command, msg, chat):
        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task)\
                                    .filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return
            task.status = 'TODO'
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task.id, task.name), chat)

    def doing(self, command, msg, chat):
        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task)\
                                     .filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return
            task.status = 'DOING'
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task.id, task.name), chat)

    def done(self, command, msg, chat):
        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task)\
                              .filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return
            task.status = 'DONE'
            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task.id, task.name), chat)

    def list(self, command, msg, chat):
        a = ''

        a += '\U0001F4CB Task List\n'
        query = db.session.query(Task)\
                                .filter_by(parents='',\
                                           chat=chat).order_by(Task.id)
        for task in query.all():
            icon = '\U0001F195'
            if task.status == 'DOING':
                icon = '\U000023FA'
            elif task.status == 'DONE':
                icon = '\U00002611'
            elif task.priority == 'priority':
                icon = 'u"\U0001F6A8"'

            a += '[[{}]] {} {}\n'.format(task.id, icon, task.name)
            a += self.deps_text(task, chat)

        self.send_message(a, chat)
        a = ''

        a += '\U0001F4DD _Status_\n'
        query = db.session.query(Task)\
                                 .filter_by(status='TODO', chat=chat)\
                                 .order_by(Task.id)
        a += '\n\U0001F195 *TODO*\n'
        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)
        query = db.session.query(Task)\
                                 .filter_by(status='DOING', chat=chat)\
                                 .order_by(Task.id)
        a += '\n\U0001F563 *DOING*\n'
        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)
        query = db.session.query(Task)\
                                 .filter_by(status='DONE', chat=chat)\
                                 .order_by(Task.id)
        a += '\n\U00002611 *DONE*\n'

        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)
        query = db.session.query(Task)\
                                 .filter_by(priority='high', chat=chat)\
                                 .order_by(Task.id)
        a += '\n\U0001F6A8 *PRIORITY*\n'
        a += '\U0001F198 high priority\n'

        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)
        query = db.session.query(Task)\
                                 .filter_by(priority='medium',\
                                 chat=chat).order_by(Task.id)
        a += '\u203C medium priority\n'


        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)
        query = db.session.query(Task)\
                                 .filter_by(priority='low', chat=chat)\
                                 .order_by(Task.id)
        a += '\u2757 low priority\n'

        for task in query.all():
            a += '\u27A1[[{}]] {}\n'.format(task.id, task.name)

        self.send_message(a, chat)

    def dependson(self, command, msg, chat):
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task).filter_by(id=task_id,\
                                                     chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return

            if text == '':
                for i in task.dependencies.split(',')[:-1]:
                    i = int(i)
                    q = db.session.query(Task).filter_by(id=i,\
                                                         chat=chat)
                    t = q.one()
                    t.parents = t.parents.replace('{},'\
                                                  .format(task.id), '')

                task.dependencies = ''
                self.send_message("Dependencies removed from task {}"\
                             .format(task_id), chat)
            else:
                for depid in text.split(' '):
                    if not depid.isdigit():
                        self.send_message("All dependencies ids must be\\\
                                      numeric, and not {}"\
                                      .format(depid), chat)
                    else:
                        depid = int(depid)
                        query = db.session.query(Task)\
                                                 .filter_by(id=depid,\
                                                 chat=chat)
                        try:
                            taskdep = query.one()
                            list_dependencies = taskdep.dependencies\
                                                       .split(',')
                            if not str(task.id) in list_dependencies:
                                taskdep.parents += str(task.id) + ','
                            else:
                                self.send_message("Essa tarefa já é filha\\\
                                              da sub tarefa", chat)
                                break
                        except sqlalchemy.orm.exc.NoResultFound:
                            self.send_message("_404_ Task {} not found x.x"\
                                         .format(depid), chat)
                            continue
                        deplist = task.dependencies.split(',')
                        if str(depid) not in deplist:
                            task.dependencies += str(depid) + ','

            db.session.commit()
            self.send_message(self.set_command_text(command)\
                         .format(task_id), chat)

    def priority(self, command, msg, chat):
        text = ''
        if msg != '':
            if len(msg.split(' ', 1)) > 1:
                text = msg.split(' ', 1)[1]
            msg = msg.split(' ', 1)[0]

        if self.check_msg_not_exists(msg):
            self.msg_no_task(chat)
        else:
            task_id = int(msg)
            query = db.session.query(Task)\
                                     .filter_by(id=task_id, chat=chat)
            try:
                task = query.one()
            except sqlalchemy.orm.exc.NoResultFound:
                self.send_message("_404_ Task {} not found x.x"\
                             .format(task_id), chat)
                return

            if text == '':
                task.priority = ''
                self.send_message("_Cleared_ all priorities from task {}"\
                             .format(task_id), chat)
            else:
                if text.lower() not in ['high', 'medium', 'low']:
                    self.send_message("The priority *must be* one of the\\\
                                 following: high, medium, low", chat)
                else:
                    task.priority = text.lower()
                    self.send_message("*Task {}* priority has priority\\\
                                 *{}*".format(task_id, text.lower()),\
                                 chat)
            db.session.commit()

    def handle_updates(self, updates):
        for update in updates["result"]:
            if 'message' in update:
                message = update['message']
            elif 'edited_message' in update:
                message = update['edited_message']
            else:
                print('Can\'t process! {}'.format(update))
                return

            command = message["text"].split(" ", 1)[0]
            msg = ''
            if len(message["text"].split(" ", 1)) > 1:
                msg = message["text"].split(" ", 1)[1].strip()

            chat = message["chat"]["id"]

            print(command, msg, chat)

            if command == '/new':
                self.new_task(command, msg, chat)

            elif command == '/rename':
                self.rename(command, msg, chat)

            elif command == '/duplicate':
                self.duplicate(command, msg, chat)

            elif command == '/delete':
                self.delete(command, msg, chat)

            elif command == '/todo':
                self.todo(command, msg, chat)

            elif command == '/doing':
                self.doing(command, msg, chat)

            elif command == '/done':
                self.done(command, msg, chat)

            elif command == '/list':
                self.list(command, msg, chat)

            elif command == '/dependson':
                self.dependson(command, msg, chat)

            elif command == '/priority':
                self.priority(command, msg, chat)

            elif command == '/start':
                self.send_message("Welcome! Here is a list of things you can do."\
                             , chat)
                self.send_message(self.HELP, chat)
                
            elif command == '/help':
                self.send_message("Here is a list of things you can do.", chat)
                self.send_message(self.HELP, chat)
            else:
                self.send_message("I'm sorry dave. I'm afraid I can't do that."\
                             , chat)

def main():
    last_update_id = None
    a = Bot()
    while True:
        print("Updates")
        updates = a.get_updates(last_update_id)

        if len(updates["result"]) > 0:
            last_update_id = a.get_last_update_id(updates) + 1
            a.handle_updates(updates)

        time.sleep(0.5)


if __name__ == '__main__':
    main()
