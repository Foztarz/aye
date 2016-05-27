from stepper_controller import StepperController
import time

class PanoramaControl:

    def __init__(self, pan_step_degrees = 10, tilt_step_degrees = 10):
        self.pan = StepperController([14, 15, 18, 23], 24, 'pan', 360) 
        self.tilt = StepperController([2, 3, 4, 17], 27, 'tilt', 180) 

        self.pan.calibrate()
        #self.tilt.calibrate()

        self.pan_step_degrees = pan_step_degrees
        self.tilt_step_degrees = tilt_step_degrees

        self.panning = True

    def step(self):
        time.sleep(0.5)
        if self.panning:
            pan_movement_succeeded = self.pan.step_degrees(self.pan_step_degrees)
            if not pan_movement_succeeded:
                print("Pan end reached at %f. Going back to origin and increasing tilt." % self.pan.degrees())
                self.pan.go_to_origin()
                #tilt_movement_succeeded = self.tilt.step_degrees(self.tilt_step_degrees)
                #if not tilt_movement_succeeded:
                #    print("Tilt end reached at %f. Panorama complete." % self.tilt.degrees())
                #    return False
        return True

    def get_status(self):
        return ("pan", self.pan.degrees()), ("tilt", self.tilt.degrees())

if __name__ == '__main__':
    panorama_control = PanoramaControl()
    while panorama_control.step():
        print("Status: %s" % str(panorama_control.get_status()))
