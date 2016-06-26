import RPi.GPIO as GPIO
import time

class StepperController:
    pin_output_sequence = [[1,0,0,0],
        [1,1,0,0],
        [0,1,0,0],
        [0,1,1,0],
        [0,0,1,0],
        [0,0,1,1],
        [0,0,0,1],
        [1,0,0,1]]

    step_delay_seconds = 0.001
    movement_direction = 1
    position = 0
    degrees_per_step = -1

    def __init__(self, stepper_pins, sensor_pin, name, degrees_range):
        self.stepper_pins = stepper_pins
        self.sensor_pin = sensor_pin
        self.name = name
        self.degrees_range = degrees_range

        GPIO.setmode(GPIO.BCM)

        for pin in self.stepper_pins:
            GPIO.setup(pin, GPIO.OUT)

        GPIO.setup(self.sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self.turn_off()

    # returns true if more movement in this direction is possible, false otherwise
    def step(self):
        self.set_stepper_pin_outputs(self.pin_output_sequence[self.current_step%8])
        self.current_step = self.current_step + self.movement_direction
        time.sleep(self.step_delay_seconds)

        if self.sensor_on():
            return False

        return True

    def degrees(self):
        return self.current_step * self.degrees_per_step

    def sensor_on(self):
        sensor_value = GPIO.input(self.sensor_pin) 
	if sensor_value is 0: 
            return False
        return True

    def set_stepper_pin_outputs(self, pin_outputs):
        for pin, output in zip(self.stepper_pins, pin_outputs):
            GPIO.output(pin, output)

    def turn_off(self):
        for pin in self.stepper_pins:
            GPIO.output(pin, 0)

    def reverse_movement_direction(self):
        self.movement_direction = -self.movement_direction

    def calibrate(self):
        self.position = 0
        self.current_step = 0
        self.movement_direction = 1

        if self.degrees_range < 360:
            print("! [%s] manually move to end position" % self.name)
            while not self.sensor_on():
                continue

        print("[%s] calibrating..." % self.name)

        while self.step():
            continue

        print("[%s] reached one end at %d" % (self.name, self.current_step))

	time.sleep(2)

        self.reverse_movement_direction()

        while not self.step():
            continue

	time.sleep(2)

        self.position = 0
        self.current_step = 0

        while self.step():
            continue

        print("[%s] reached other end at %d" % (self.name, self.current_step))

	time.sleep(2)

        self.degrees_per_step = abs(float(self.degrees_range) / self.current_step)

        print("[%s] calibrated. degrees per step: %f" % (self.name, self.degrees_per_step))

        self.reverse_movement_direction()

        while not self.step():
            continue

	self.turn_off()
