from twisted.internet import defer

from spiral.curvecp._pynacl.server import CurveCPServerDispatcher
from spiral.curvecp._pynacl.transport import CurveCPClientTransport


class CurveCPClientEndpoint(object):
    def __init__(self, reactor, host, port, serverKey, serverExtension, clientKey=None,
                 clientExtension='\x00' * 16, congestion=None):
        self.reactor = reactor
        self.host = host
        self.port = port
        self.serverKey = serverKey
        self.serverExtension = serverExtension
        self.clientKey = clientKey
        self.clientExtension = clientExtension
        self.congestion = congestion

    def connect(self, fac):
        transport = CurveCPClientTransport(
            self.reactor, self.serverKey, fac, self.host, self.port,
            self.serverExtension, self.clientKey, self.clientExtension,
            self.congestion)
        listeningPort = self.reactor.listenUDP(0, transport)
        transport.notifyFinish().addCallback(self._clientFinished, listeningPort)
        return transport._deferred

    def _clientFinished(self, ign, listeningPort):
        listeningPort.stopListening()


class CurveCPServerEndpoint(object):
    def __init__(self, reactor, serverKey, port, congestion=None):
        self.reactor = reactor
        self.serverKey = serverKey
        self.port = port
        self.congestion = congestion

    def listen(self, fac):
        dispatcher = CurveCPServerDispatcher(self.reactor, self.serverKey, fac, self.congestion)
        return defer.succeed(self.reactor.listenUDP(self.port, dispatcher))
