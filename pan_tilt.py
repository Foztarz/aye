from stepper_controller import StepperController

pan = StepperController([14, 15, 18, 23], 10, 'pan', 360) 

pan.calibrate()
