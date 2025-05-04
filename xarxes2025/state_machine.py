class State_machine:
    """
    RTSP protocol state machine implementation.
    Manages state transitions for the streaming protocol.
    Ensures valid state changes according to RTSP specification.
    """

    def __init__(self):
        """
        Initialize state machine.
        
        Sets up:
        - Initial state as INIT
        - Valid state transitions dictionary
        - Possible states: INIT, READY, PLAYING
        """
        # Initial state
        self.state = "INIT"

        # Possible transitions dictionary
        # Format: current_state: {event: next_state}
        self.transitions = {
            'INIT': {'SETUP': 'READY'},
            'READY': {'PLAY': 'PLAYING', 'TEARDOWN': 'INIT'},
            'PLAYING': {'PAUSE': 'READY', 'TEARDOWN': 'INIT'}
        }
    
    def transition(self, event):
        """
        Attempt to transition to a new state based on event.

        Args:
            event (str): The event triggering the transition (SETUP/PLAY/PAUSE/TEARDOWN)

        Returns:
            bool: True if transition is valid and executed, False otherwise

        Validates the transition according to the RTSP state machine rules.
        Updates state if transition is valid.
        """
        if event in self.transitions[self.state]:
            self.state = self.transitions[self.state][event]
            return True
        else:
            return False
        
    def get_state(self):
        """
        Get current state of the state machine.

        Returns:
            str: Current state (INIT/READY/PLAYING)

        Used to check current state before processing commands.
        """
        return self.state