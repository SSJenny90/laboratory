from . import furnace,lcr,motor,mfc,daq

def get_ports():
    '''Returns a list of available serial ports for connecting to the furnace and motor

    :returns: list of available ports
    :rtype: list, str
    '''
    return [comport.device for comport in list_ports.comports()]

def load_instruments():
    return lcr.LCR(), daq.DAQ(), mfc.MFC(), furnace.Furnace(), motor.Motor()

def reconnect(lab_obj):

    ports = get_ports()

    if not ports: return
    if not lab_obj.lcr.status: lab_obj.lcr = LCR()
    if not lab_obj.daq.status: lab_obj.daq = DAQ()
    if not lab_obj.mfc.status: lab_obj.mfc = MFC()
    if not lab_obj.furnace.status: lab_obj.furnace = Furnace()
    if not lab_obj.motor.status: lab_obj.motor = Motor()
