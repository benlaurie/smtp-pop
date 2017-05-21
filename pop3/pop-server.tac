"""
An example pop3 server
"""

# run with twistd-2.7 -ny pop-server.tac

import os.path
from stat import S_ISREG, ST_MODE, ST_CTIME

from twisted.application import internet, service
from twisted.cred.portal import Portal, IRealm
from twisted.internet.protocol import ServerFactory
from twisted.logger import Logger
from twisted.mail import pop3
from twisted.mail.maildir import MaildirMailbox
from twisted.mail.pop3 import IMailbox
from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from zope.interface import implements
from itertools import repeat
from hashlib import md5
from StringIO import StringIO

class SimpleMailbox:
    implements(IMailbox)

    def __init__(self):
        message = """From: me
To: you
Subject: A test mail

Hello world!"""
        self.messages = [m for m in repeat(message, 20)]


    def listMessages(self, index=None):
        if index != None:
            return len(self.messages[index])
        else:
            return [len(m) for m in self.messages]

    def getMessage(self, index):
        return StringIO(self.messages[index])

    def getUidl(self, index):
        return md5(self.messages[index]).hexdigest()

    def deleteMessage(self, index):
        pass

    def undeleteMessages(self):
        pass

    def sync(self):
        pass

# Works, even though it is not complete
class DiskMailbox:
    implements(IMailbox)

    def __init__(self, user):
        self.user = user
        dirpath = os.path.join("..", "mailbox", self.user)
        entries = ((os.path.join(dirpath, fn)) for fn in os.listdir(dirpath))
        entries = ((os.stat(path), path) for path in entries)
        # leave only regular files, insert creation date
        entries = ((stat[ST_CTIME], path)
                   for stat, path in entries if S_ISREG(stat[ST_MODE]))
        self.messages = []
        for stat, fn in entries:
            with open(fn) as f:
                self.messages.append(f.read())

    def listMessages(self, index=None):
        if index != None:
            return len(self.messages[index])
        else:
            return [len(m) for m in self.messages]

    def getMessage(self, index):
        return StringIO(self.messages[index])

    def getUidl(self, index):
        return md5(self.messages[index]).hexdigest()

    def deleteMessage(self, index):
        pass

    def undeleteMessages(self):
        pass

    def sync(self):
        pass


class SimpleRealm:
    implements(IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IMailbox in interfaces:
            #return IMailbox, SimpleMailbox(), lambda: None
            #return IMailbox, DiskMailbox(avatarId + "@test.org"), lambda: None
            return IMailbox, MaildirMailbox(os.path.join("..", "mailbox", avatarId + "@test.org")), lambda: None
        else:
            raise NotImplementedError()

class DebugPassword(InMemoryUsernamePasswordDatabaseDontUse):
    log = Logger(namespace="password")
    
    def requestAvatarId(self, credentials):
        self.log.info(credentials.username)
        return InMemoryUsernamePasswordDatabaseDontUse.requestAvatarId(self, credentials)


portal = Portal(SimpleRealm())

checker = DebugPassword()
checker.addUser("ben", "password")
portal.registerChecker(checker)

application = service.Application("example pop3 server")

f = ServerFactory()
f.protocol = pop3.POP3
f.protocol.portal = portal
internet.TCPServer(1230, f).setServiceParent(application)
