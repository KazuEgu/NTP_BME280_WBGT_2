from machine import I2C
import time

class RW1063LCD:
    def __init__(self, i2c: I2C, addr: int = 0x3F):
        self.i2c = i2c
        self.addr = addr
        self.init_lcd()

    def write_cmd(self, cmd):
        try:
            self.i2c.writeto(self.addr, bytes([0x00, cmd]))
            time.sleep_ms(2)
        except OSError:
            print("I2C Write Error (CMD)")

    def write_data(self, data):
        try:
            self.i2c.writeto(self.addr, bytes([0x40, data]))
            time.sleep_ms(2)
        except OSError:
            print("I2C Write Error (DATA)")

    def init_lcd(self):
        time.sleep_ms(50)
        self.write_cmd(0x38)  # 8-bit, 2 line
        self.write_cmd(0x39)  # Function set with IS=1 (extended instruction)
        self.write_cmd(0x14)  # Internal OSC freq
        self.write_cmd(0x70)  # Contrast low bits
        self.write_cmd(0x5E)  # Icon/Contrast/Power
        self.write_cmd(0x6C)  # Follower control
        time.sleep_ms(200)
        self.write_cmd(0x38)  # Back to normal mode
        self.write_cmd(0x0C)  # Display ON
        self.write_cmd(0x01)  # Clear display
        time.sleep_ms(2)

    def clear(self):
        self.write_cmd(0x01)
        time.sleep_ms(2)

    def move_to(self, col, row):
        # RW1063 (ACM2004) uses non-linear DDRAM addresses
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        if row > 3:
            row = 3
        self.write_cmd(0x80 | (row_offsets[row] + col))

    def putstr(self, string):
        for char in string:
            self.write_data(ord(char))
