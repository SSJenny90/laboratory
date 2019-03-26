from . import furnace,lcr,motor,gas_controllers,daq

def get_ports():
    '''Returns a list of available serial ports for connecting to the furnace and motor

    :returns: list of available ports
    :rtype: list, str
    '''
    return [comport.device for comport in list_ports.comports()]

def connect():
    return lcr.LCR(), daq.DAQ(), gas_controllers.GasControllers(), furnace.Furnace(), motor.Motor()

def reconnect(lab_obj):

    # ports = get_ports()

    # if not ports: return
    if not lab_obj.lcr.status: lab_obj.lcr = LCR()
    if not lab_obj.daq.status: lab_obj.daq = DAQ()
    if not lab_obj.gas.status: lab_obj.gas = GasControllers()
    if not lab_obj.furnace.status: lab_obj.furnace = Furnace()
    if not lab_obj.motor.status: lab_obj.motor = Motor()
    else:
        print('All instruments are connected!')
