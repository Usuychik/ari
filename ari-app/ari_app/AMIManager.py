import panoramisk.manager as manager

#rewrite panoramisk.Manager with connected property
class AMIManager(manager.Manager):
    def __init__(self, **config):
        super().__init__(**config)

    def connection_lost(self, exc):
        self._connected = False
        super().connection_lost(exc)

    def login(self, future):
        authenticated = super().login(future)
        self._connected = authenticated
        return authenticated

    @property
    def connected(self):
        return self._connected



