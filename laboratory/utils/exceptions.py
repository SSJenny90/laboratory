class Error(Exception):
    pass

class InstrumentError(Error):
    pass

class InstrumentCommunicationError(Error):
    pass

class InstrumentConnectionError(Error):
    pass

class SetupError(Error):
    pass