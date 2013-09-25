import argparse
import os

from nacl.public import PublicKey
from twisted.internet.task import react
from twisted.internet import defer, protocol

from spiral.curvecp.pynacl.endpoints import CurveCPClientEndpoint
from spiral.curvecp.keydir import Keydir


class CurveCPMClientProcessProtocol(protocol.ProcessProtocol):
    def __init__(self, proto):
        self.proto = proto

    def childDataReceived(self, fd, data):
        assert fd == 7
        self.proto.transport.write(data)

    def childConnectionLost(self, fd):
        if fd == 7:
            self.proto.transport.loseConnection()

    def processEnded(self, status):
        self.proto.childProcessEnded = True


class CurveCPMClientProtocol(protocol.Protocol):
    def __init__(self):
        self.processProto = CurveCPMClientProcessProtocol(self)
        self.deferred = defer.Deferred()
        self.childProcessEnded = False

    def connectionMade(self):
        env = os.environ.copy()
        env.update(self.transport.getHost().asUCSPIEnv('client', 'client'))
        env.update(self.transport.getPeer().asUCSPIEnv('client', 'server'))
        self.factory.reactor.spawnProcess(
            self.processProto, self.factory.args.program,
            args=[self.factory.args.program] + self.factory.args.argv,
            env=env, childFDs={
                0: 0, 1: 1, 2: 2, 6: 'w', 7: 'r'})

    def dataReceived(self, data):
        if not self.childProcessEnded:
            self.processProto.transport.writeToChild(6, data)

    def readConnectionLost(self):
        if not self.childProcessEnded:
            self.processProto.transport.closeChildFD(6)

    def connectionLost(self, status):
        self.deferred.callback(None)


class CurveCPMClientFactory(protocol.ClientFactory):
    def __init__(self, reactor, args):
        self.reactor = reactor
        self.args = args

    protocol = CurveCPMClientProtocol


def twistedMain(reactor, args):
    fac = CurveCPMClientFactory(reactor, args)
    e = CurveCPClientEndpoint(
        reactor, args.host, args.port,
        serverKey=PublicKey(args.key.decode('hex')),
        serverExtension=args.server_extension.decode('hex'),
        clientKey=args.client_keydir,
        clientExtension=args.client_extension.decode('hex'))
    d = e.connect(fac)
    d.addCallback(lambda proto: proto.deferred)
    return d

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name')
    parser.add_argument('-e', '--server-extension', default='0' * 32)
    parser.add_argument('-k', '--client-keydir', type=Keydir)
    parser.add_argument('--client-extension', default='0' * 32)
    parser.add_argument('key')
    parser.add_argument('host')
    parser.add_argument('port', type=int)
    parser.add_argument('program')
    parser.add_argument('argv', nargs='*')

    react(twistedMain, [parser.parse_args()])
