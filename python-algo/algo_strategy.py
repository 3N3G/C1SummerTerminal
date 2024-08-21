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
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global WALL, SUPPORT, TURRET, SCOUT, DEMOLISHER, INTERCEPTOR, MP, SP
        WALL = config["unitInformation"][0]["shorthand"]
        SUPPORT = config["unitInformation"][1]["shorthand"]
        TURRET = config["unitInformation"][2]["shorthand"]
        SCOUT = config["unitInformation"][3]["shorthand"]
        DEMOLISHER = config["unitInformation"][4]["shorthand"]
        INTERCEPTOR = config["unitInformation"][5]["shorthand"]
        self.MP = 0
        self.SP = 0
        self._to_spawn = (15, 1)
        self.scored_on_locations = []
        self.defense_line = [[2, 13], [7, 13], [12, 13], [17, 13], [22, 13], [27, 11]]

    def on_turn(self, turn_state):
        game_state = gamelib.GameState(self.config, turn_state)
        self.update_info(game_state)

        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)

        self.build_defenses(game_state)
        self.build_support_diagonal(game_state)
        self.deploy_scouts(game_state)

        game_state.submit_turn()

    def build_defenses(self, game_state):
        self.update_info(game_state)
        for location in self.defense_line:
            if game_state.can_spawn(WALL, location):
                game_state.attempt_spawn(WALL, location)
            
            turret_location = (location[0], location[1] - 1)
            if game_state.can_spawn(TURRET, turret_location):
                game_state.attempt_spawn(TURRET, turret_location)

    def build_support_diagonal(self, game_state):
        self.update_info(game_state)
        while game_state.can_spawn(SUPPORT, self._to_spawn):
            game_state.attempt_spawn(SUPPORT, self._to_spawn)
            if self._to_spawn[0] + self._to_spawn[1] == 16 and self._to_spawn[0] == 3:
                self._to_spawn = (13, 0)
            else:
                self._to_spawn = (self._to_spawn[0] - 1, self._to_spawn[1] + 1)

    def deploy_scouts(self, game_state):
        self.update_info(game_state)
        scout_cost = game_state.type_cost(SCOUT)[1]
        num_scouts = int(self.MP // scout_cost)
        # gamelib.debug_write(num_scouts)
        # gamelib.debug_write(num_scouts//2)
        deploy_locations = [[14, 0]]
        
        for location in deploy_locations:
            game_state.attempt_spawn(SCOUT, location, num_scouts // 2)

    def update_info(self, game_state):
        self.MP = game_state.get_resource(1)
        self.SP = game_state.get_resource(0)

if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()