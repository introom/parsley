from __future__ import absolute_import

from twisted.trial import unittest
from twisted.python.compat import iterbytes


from ometa.grammar import OMeta
from ometa.tube import TrampolinedParser


class TrampolinedReceiver():
    """
    Receive and store the passed in data.
    """

    currentRule = 'initial'

    def __init__(self):
        self.received = []

    def receive(self, data):
        self.received.append(data)


class TrampolinedParserTestCase(unittest.SynchronousTestCase):
    """
    Tests for L{ometa.tube.TrampolinedParser}
    """

    def _parseGrammar(self, grammar, name="Grammar"):
        return OMeta(grammar).parseGrammar(name)

    def setUp(self):
        _grammar =  r"""
            delimiter = '\r\n'
            initial = <(~delimiter anything)*>:val delimiter -> receiver.receive(val)
            witharg :arg1 :arg2 = <(~delimiter anything)*>:a delimiter -> receiver.receive(arg1+arg2+a)

            bindings = digit:d (-> int(d)+SMALL_INT):val -> receiver.receive(val)
            items = <anything{2}>:item -> receiver.receive(item)
        """
        self.grammar = self._parseGrammar(_grammar)

    def test_dataNotFullyReceived(self):
        """
        Since the initial rule inside the grammar is not matched, the receiver
        shouldn't receive any byte.
        """
        receiver = TrampolinedReceiver()
        trampolinedParser = TrampolinedParser(self.grammar, receiver, {})
        buf = b'foobarandnotreachdelimiter'
        for c in iterbytes(buf):
            trampolinedParser.receive(c)
        self.assertEqual(receiver.received, [])


    def test_dataFullyReceived(self):
        """
        The receiver should receive the data according to the grammar.
        """
        receiver = TrampolinedReceiver()
        trampolinedParser = TrampolinedParser(self.grammar, receiver, {})
        buf = b'\r\n'.join((b'foo', b'bar', b'foo', b'bar'))
        for c in iterbytes(buf):
            trampolinedParser.receive(c)
        self.assertEqual(receiver.received, [b'foo', b'bar', b'foo'])
        trampolinedParser.receive('\r\n')
        self.assertEqual(receiver.received, [b'foo', b'bar', b'foo', b'bar'])


    def test_bindings(self):
        """
        The passed-in bindings should be accessible inside the grammar.
        """
        receiver = TrampolinedReceiver()
        bindings = {'SMALL_INT': 3}
        receiver.currentRule = "bindings"
        TrampolinedParser(self.grammar, receiver, bindings).receive('0')
        self.assertEqual(receiver.received, [3])


    def test_currentRuleWithArgs(self):
        """
        TrampolinedParser should be able to invoke curruent rule with args.
        """
        receiver = TrampolinedReceiver()
        receiver.currentRule = "witharg", "nice ", "day"
        trampolinedParser = TrampolinedParser(self.grammar, receiver, {})
        buf = b' oh yes\r\n'
        for c in iterbytes(buf):
            trampolinedParser.receive(c)
        self.assertEqual(receiver.received, ["nice day oh yes"])


    def test_pauseParsing(self):
        """
        TrampolinedParser should be able to pause parsing.
        """
        receiver = TrampolinedReceiver()
        receiver.currentRule = "items"
        trampolinedParser = TrampolinedParser(self.grammar, receiver, {})
        teststring = b'whatanicedayitis'
        buf = [teststring[i:i+2] for i in range(0, len(teststring), 2)]
        for c in buf[:2]:
            trampolinedParser.receive(c)
        trampolinedParser._interp.paused = True
        for c in buf[2:]:
            trampolinedParser.receive(c)
        self.assertEqual(['wh', 'at'], receiver.received)
        trampolinedParser._interp.paused = False
        trampolinedParser.receive(b'')
        self.assertEqual(buf, receiver.received)


