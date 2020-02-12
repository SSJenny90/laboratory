class Error(Exception):
    pass

class InstrumentError(Error):
    pass

class InstrumentReadError(InstrumentError):
    pass

class InstrumentWriteError(InstrumentError):
    pass

class InstrumentCommunicationError(Error):
    pass

class InstrumentConnectionError(Error):
    pass

class SetupError(Error):
    pass

class CalibrationError(Error):
    pass