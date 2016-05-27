import RPi.GPIO as GPIO
import time

def positive_answer(y_or_n):
    if len(y_or_n) == 0 or y_or_n[0] == 'y':
        return True
    return False

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
    degrees_per_step = -1
    current_step = 0

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

    def steps_from_degrees(self, degrees):
        return degrees / self.degrees_per_step

    def step_degrees(self, degrees):
        desired_step = self.current_step + int(self.steps_from_degrees(degrees))
        starting_degrees = self.degrees()
        print("Current step: %d Desired step %d" % (self.current_step, desired_step))

        if degrees > 0:
            self.movement_direction = 1
        else:
	    self.movement_direction = -1 
            
        while self.current_step != desired_step:
            if not self.step():
                print("Moved %d degrees before reaching an end" % (self.degrees() - starting_degrees))
	        self.turn_off()
                return False

	self.turn_off()
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

        print("[%s] calibrating..." % self.name)

        if self.degrees_range < 360:
            for count in range(300):
                self.step()
            y_or_n = raw_input("! [%s] Am I moving away from the switch? (y/n)" % self.name)
            if not positive_answer(y_or_n):
                self.reverse_movement_direction()

            y_or_n = 'y'
            while positive_answer(y_or_n):
                for count in range(300):
                    self.step()
                y_or_n = raw_input('! [%s] Can I continue? (y/n)' % self.name)
	else:
            while self.step():
                continue

        print("[%s] reached one end at %d" % (self.name, self.current_step))


	time.sleep(0.5)

        self.reverse_movement_direction()

        while not self.step():
            continue

	time.sleep(0.5)

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
 	
	self.current_step = 0

	self.turn_off()

    def go_to_origin(self):
        if self.sensor_on():
            self.reverse_movement_direction()
            while not self.step():
                continue

        if self.current_step > 0:
            self.movement_direction = -1
        else:
            self.movement_direction = 1
        
        while self.current_step != 0:
            self.step()
