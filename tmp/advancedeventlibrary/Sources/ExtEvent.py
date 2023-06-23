from Components.Element import cached
from Components.Sources.Source import Source

class ExtEvent(Source, object):

    def __init__(self):
        Source.__init__(self)
        self.srv = None
        self.evt = None

    @cached
    def getCurrentService(self):
        return self.srv

    @cached
    def getCurrentEvent(self):
        return self.evt

    event = property(getCurrentEvent)
    service = property(getCurrentService)

    def newService(self, ref):
        if not self.srv or self.srv != str(ref):
            self.srv = str(ref)
            if not ref:
                self.changed((self.CHANGED_CLEAR,))
            elif self.evt and self.srv:
                self.changed((self.CHANGED_ALL,))

    def newEvent(self, event):
        if not self.evt or self.evt != event:
            self.evt = event
            if not event:
                self.changed((self.CHANGED_CLEAR,))
            elif self.evt and self.srv:
                self.changed((self.CHANGED_ALL,))