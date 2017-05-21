# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

# You can run this module directly with:
#    twistd -ny emailserver.tac

"""
A little less toy email server.
"""
from __future__ import print_function

from hashlib import sha256
import os.path

from zope.interface import implementer

from twisted.internet import defer
from twisted.logger import Logger
from twisted.mail import smtp
from twisted.mail.imap4 import LOGINCredentials, PLAINCredentials

from twisted.cred.checkers import InMemoryUsernamePasswordDatabaseDontUse
from twisted.cred.portal import IRealm
from twisted.cred.portal import Portal



@implementer(smtp.IMessageDelivery)
class ConsoleMessageDelivery:
    log = Logger(namespace="smtp-server")
    
    def receivedHeader(self, helo, origin, recipients):
        return "Received: ConsoleMessageDelivery"

    
    def validateFrom(self, helo, origin):
        # All addresses are accepted
        return origin

    
    def validateTo(self, user):
        self.log.info("user: {user}", user=user.dest)
        # Only messages directed to the "console" user are accepted.
        if user.dest.local == "console":
            return lambda: ConsoleMessage()
        elif str(user.dest) == "ben@test.org":
            return lambda: DeliverMessage(str(user.dest))
        raise smtp.SMTPBadRcpt(user)


@implementer(smtp.IMessage)
class DeliverMessage:
    def __init__(self, dest):
        self.dest = dest
        self.lines = []

    
    def lineReceived(self, line):
        self.lines.append(line)

    
    def eomReceived(self):
        print("New message received:")
        msg = "\n".join(self.lines)
        self.lines = None

        print(msg)
        fn = sha256(msg).hexdigest()
        with open(os.path.join("..", "mailbox", self.dest, fn), "w") as f:
            f.write(msg)
        
        return defer.succeed(None)

    
    def connectionLost(self):
        # There was an error, throw away the stored lines
        self.lines = None

    
@implementer(smtp.IMessage)
class ConsoleMessage:
    def __init__(self):
        self.lines = []

    
    def lineReceived(self, line):
        self.lines.append(line)

    
    def eomReceived(self):
        print("New message received:")
        print("\n".join(self.lines))
        self.lines = None
        return defer.succeed(None)

    
    def connectionLost(self):
        # There was an error, throw away the stored lines
        self.lines = None



class ConsoleSMTPFactory(smtp.SMTPFactory):
    protocol = smtp.ESMTP

    def __init__(self, *a, **kw):
        smtp.SMTPFactory.__init__(self, *a, **kw)
        self.delivery = ConsoleMessageDelivery()
    

    def buildProtocol(self, addr):
        p = smtp.SMTPFactory.buildProtocol(self, addr)
        p.delivery = self.delivery
        p.challengers = {"LOGIN": LOGINCredentials, "PLAIN": PLAINCredentials}
        return p



@implementer(IRealm)
class SimpleRealm:
    def requestAvatar(self, avatarId, mind, *interfaces):
        if smtp.IMessageDelivery in interfaces:
            return smtp.IMessageDelivery, ConsoleMessageDelivery(), lambda: None
        raise NotImplementedError()



def main():
    from twisted.application import internet
    from twisted.application import service    
    
    portal = Portal(SimpleRealm())
    checker = InMemoryUsernamePasswordDatabaseDontUse()
    checker.addUser("guest", "password")
    portal.registerChecker(checker)
    
    a = service.Application("Console SMTP Server")
    internet.TCPServer(2500, ConsoleSMTPFactory(portal)).setServiceParent(a)
    
    return a

application = main()
