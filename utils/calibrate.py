import loggers


def furnace_profile(self):
    """Records the temperature of both electrodes (te1 and te2) as the sample is moved
    from one end of the stage to the other. Used to find the center of the stage or the xpos of a desired temperature gradient when taking thermopower measurements.
    """
    self.daq.configure()
    self.motor.set_xpos(4000)
    Utils.save_obj(self.data,'furnace_profile')
    xpos = 4000
    while xpos < 6000:
        xpos = self.motor.get_pos()
        self.data.xpos.append(xpos)
        vals = self.daq.get_temp()
        self.data.thermo.tref.append(vals[0])
        self.data.thermo.te1.append(vals[1])
        self.data.thermo.te2.append(vals[2])

        self.motor.move_mm(.1)

        Utils.save_obj(self.data,'furnace_profile')
        time.sleep(600)

def find_center(self):
    """TODO - Attempts to place the sample at the center of the heat source such that
    te1 = te2. untested.
    """
    self.daq.reset()
    self.daq.toggle_switch('thermo')
    self.daq._config_temp()

    while True:
        temp = self.daq.get_temp()

        if temp is None:
            self.logger.error('No temperature data collected')
        te1 = temp[1]
        te2 = temp[2]

        print(te1,te2)

        delta = abs(te1-te2)

        if delta < 0.1:
            print('Found center at' + self.motor.get_pos())
            break

        if te1 < te2:
            self.motor.move_mm(-0.05)
        elif te2 < te1:
            self.motor.move_mm(0.05)
        print(self.motor.get_pos())

        time.sleep(600)
