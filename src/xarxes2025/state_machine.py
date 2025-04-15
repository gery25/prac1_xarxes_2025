class State_machine :
    def __init__(self):
        #estat inicial
        self.state = "INIT"

        # Trancicions possibles
        self.transitions = {
            'INIT': {'SETUP': 'READY'},
            'READY': {'PLAY': 'PLAYING', 'TEARDOWN': 'INIT'},
            'PLAYING': {'PAUSE': 'READY', 'TEARDOWN': 'INIT'}
        }
    
    def transition(self, event):
        if event in self.transitions[self.state]:
            self.state = self.transitions[self.state][event]
            return True
        else:
            return False
        
    def get_state(self):
        return self.state