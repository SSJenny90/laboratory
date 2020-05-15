class InstrumentError(Exception):
    pass

class InstrumentReadError(InstrumentError):
    """An error has occured while reading one of the instruments"""
    pass

class InstrumentWriteError(InstrumentError):
    pass

class InstrumentCommunicationError(Exception):
    pass

class InstrumentConnectionError(Exception):
    pass

class SetupError(Exception):
    pass

class CalibrationError(Exception):
    pass