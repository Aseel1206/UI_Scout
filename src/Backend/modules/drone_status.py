# singleton.py
class DroneState:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DroneState, cls).__new__(cls)
            cls._instance.current_mode = None
            cls._instance.is_armed = False
        return cls._instance


# Use this to get the instance
drone_state = DroneState()


# if there is no Drone state is createst one with current mode set to none and armed is false 
# also it makes sure that the entire program uses only drone state throught the program
# it justs creates a new instance for the class DroneState if it is not present 