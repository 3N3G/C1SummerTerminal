import gamelib
import random
import math
import warnings
from sys import maxsize
import json


"""
Most of the algo code you write will be in this file unless you create new
modules yourself. Start by modifying the 'on_turn' function.

Advanced strategy tips: 

  - You can analyze action frames by modifying on_action_frame function

  - The GameState.map object can be manually manipulated to create hypothetical 
  board states. Though, we recommended making a copy of the map to preserve 
  the actual current map state.
"""

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        MP = 1
        SP = 0
        # This is a good place to do initial setup
        #GENE track the newest support to build (first from 15,1 up and left to 3,13, then down to 13,0 through 0,13)
        self._to_spawn = (15, 1)
        self.scored_on_locations = []

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        SP = game_state.get_resource(0) #GENE get building resources
        MP = game_state.get_resource(1) #GENE get troop resources

        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  #Comment or remove this line to enable warnings.

        
        # self.starter_strategy(game_state) #GENE emove this complicated stuff
        #GENE START
        
        # First try to put as many scouts as possible (5) at (14,0)
        gamelib.debug_write("MP: ") # This is how to debug print
        gamelib.debug_write(int(MP))
        gamelib.debug_write("scout cost: ")
        gamelib.debug_write(game_state.type_cost(SCOUT))


        gamelib.debug_write(game_state.attempt_spawn(SCOUT, [14,0], int(MP) // int(game_state.type_cost(SCOUT)[1]))) # will print out how many are sent
        gamelib.debug_write("THE New MP: ")
        gamelib.debug_write("IS " + str(game_state.get_resource(1)))

        # Now put support buildings aside the path that the (14,0) scouts will take
        while game_state.can_spawn(SUPPORT, self._to_spawn):
            game_state.attempt_spawn(SUPPORT, self._to_spawn) #
            if self._to_spawn[0] + self._to_spawn[1] == 16 and self._to_spawn[0] == 3: # on first diagonal and should change
                self._to_spawn = (13,0)
            else: # just go up left along diagonal
                self._to_spawn = (self._to_spawn[0] - 1, self._to_spawn[1] + 1)
        
        # GENE END
            
        game_state.submit_turn()


if __name__ == "__main__":

    algo = AlgoStrategy()
    algo.start()
