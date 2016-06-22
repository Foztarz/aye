from stepper_controller import StepperController
import time

class PanoramaControl:
    pan = None
    tilt = None

    def __init__(self, use_pan = True, use_tilt = True, pan_step_degrees = 30, tilt_step_degrees = 20):
        self.pan = StepperController([14, 15, 18, 23], 24, 'pan', 360) 
        self.tilt = StepperController([2, 3, 4, 17], 27, 'tilt', 90) 

        self.use_pan = use_pan
        self.use_tilt = use_tilt

        if use_pan:
            self.pan.calibrate()
        if use_tilt:
            self.tilt.calibrate()

        self.pan_step_degrees = pan_step_degrees
        self.tilt_step_degrees = tilt_step_degrees

        self.last_pan = False
        if not self.use_tilt:
            self.last_pan = True

    def step(self):
        time.sleep(0.5)
        if self.use_pan:
            pan_movement_succeeded = self.pan.step_degrees(self.pan_step_degrees)
            if not pan_movement_succeeded:
                print("Pan end reached at %f." % self.pan.degrees())
                if self.last_pan:
                    print("Panorama complete at pan: %f tilt: %f" % (self.pan.degrees(), self.tilt.degrees()))
                    return False

                print("Going back to origin and increasing tilt.")
                self.pan.go_to_origin()
                tilt_movement_succeeded = self.tilt.step_degrees(self.tilt_step_degrees)
                if not tilt_movement_succeeded:
                    print("Tilt end reached at %f. Panorama complete after final pan." % self.tilt.degrees())
                    self.last_pan = True
                    return True

        return True

    def get_status(self):
        return ("pan", self.pan.degrees()), ("tilt", self.tilt.degrees())

if __name__ == '__main__':
    panorama_control = PanoramaControl()
    while panorama_control.step():
        print("Status: %s" % str(panorama_control.get_status()))
