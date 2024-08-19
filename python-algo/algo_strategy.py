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
        # game_state.attempt_spawn(DEMOLISHER, [24, 10], 3) # STELLA line needed to submit algo on website

        gamelib.debug_write(
            'Performing turn {} of your custom algo strategy'.format(
                game_state.turn_number))
        game_state.suppress_warnings(
            True)  #Comment or remove this line to enable warnings.

        self.defense_strategy(game_state)

        game_state.submit_turn()

    def defense_strategy(self, game_state):
        '''
        STELLA
        This is a passive, overall defensive algorithm that has hardcoded locations for turrets, walls, and sends out interceptors occasionally
        For offensive, we will send out a troop of demolishers and scouts after hoarding enough mobile units
        '''

        # First, place basic defenses
        self.build_defences(game_state)

        # Now build reactive defenses based on where the enemy scored
        self.build_reactive_defense(game_state)

        # If the turn is less than 5, stall with interceptors and wait to see enemy's base
        if game_state.turn_number < 5:
            pass
            # self.stall_with_interceptors(game_state)
        else:
            # Figure out their least defended area and send Scouts there.
            # Only spawn Scouts when we have over 10 MP
            # Sending more at once is better since attacks can only hit a single scout at a time
            if game_state.get_resource(MP) >= 10:
                scout_spawn_location_options = [[18, 4], [10, 3], [17, 3],
                                                [11, 2], [16, 2], [12, 1],
                                                [15, 1], [13, 0], [14, 0]]
                best_location = self.least_damage_spawn_location(
                    game_state, scout_spawn_location_options)
                game_state.attempt_spawn(SCOUT, best_location, 1000)

        # Lastly, if we have spare SP, let's build some supports
        support_locations = [[13, 2], [14, 2], [13, 3], [14, 3]]
        game_state.attempt_spawn(SUPPORT, support_locations)

        # if we have even more SP, build, build more turrets
        extra_turret_locations = [[3, 12], [23, 12], [4, 12], [24, 12],
                                  [9, 10], [14, 10], [19, 10]]
        game_state.attempt_spawn(TURRET, extra_turret_locations)
        game_state.attempt_upgrade(extra_turret_locations)

    def build_defences(self, game_state):
        """
        STELLA
        Build basic defenses using hardcoded locations.

        Our priorities regarding structure point is as follows:
        1. build turrets in desired locations
        2. build walls in desired locations for protation
        3. upgrade certain turrets
        4. build more walls
        5. upgrade certain walls 
        6. build more turrets WOAH
        
        we start with 40 structure units + 5 (x != 1) + 1 * (x // 10) + 1 * num of damage dealt to opponent on round x - 1, where x is the round num we are on

        each turret cost 3, upgrade cost 5 
        each wall cost 2, upgrade cost 2

        upgrade turrets first because scout damage range is longer than basic turret
        """
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # Community tools available at: https://terminal.c1games.com/rules#Download

        # Place turrets on second row
        turret_locations = [[2, 12], [25, 12], [7, 12], [20, 12], [12, 12],
                            [15, 12]]
        # attempt_spawn will try to spawn units if we have resources, and will check if a blocking unit is already there
        # note that list order matters here since attempt_spawn iterates the list
        game_state.attempt_spawn(TURRET, turret_locations)

        # Place walls in front of turrets to soak up damage for them
        wall_locations = [[2, 13], [25, 13], [12, 13], [15, 13]]
        game_state.attempt_spawn(WALL, wall_locations)

        # upgrade turret so they have longer attack range
        game_state.attempt_upgrade(turret_locations)

        # build secondary walls so enemy need to take longer paths
        sec_wall_locations = [(0, 13), (27, 13), (1, 13), (26, 13)]
        game_state.attempt_spawn(WALL, sec_wall_locations)

        # upgrade walls so they soak more damage
        game_state.attempt_upgrade([[2, 12], [25, 12]])

        # build secondary turrets (by this point game should've ended, i think)
        sec_turret_locations = [[1, 12], [26, 12], [3, 12], [24, 12], [6, 12],
                                [19, 12]]
        game_state.attempt_spawn(TURRET, turret_locations)

    def build_reactive_defense(self, game_state):
        """
        This function builds reactive defenses based on where the enemy scored on us from.
        We can track where the opponent scored by looking at events in action frames 
        as shown in the on_action_frame function
        """
        for location in self.scored_on_locations:
            # Build turret one space above so that it doesn't block our own edge spawn locations
            build_location = [location[0], location[1] + 1]
            game_state.attempt_spawn(TURRET, build_location)

    def stall_with_interceptors(self, game_state):
        """
        Send out interceptors at random locations to defend our base from enemy moving units when we have enough wealth
        """
        # We can spawn moving units on our edges so a list of all our edge locations
        friendly_edges = game_state.game_map.get_edge_locations(
            game_state.game_map.BOTTOM_LEFT
        ) + game_state.game_map.get_edge_locations(
            game_state.game_map.BOTTOM_RIGHT)

        # Remove locations that are blocked by our own structures
        # since we can't deploy units there.
        deploy_locations = self.filter_blocked_locations(
            friendly_edges, game_state)

        # While we have remaining MP to spend lets send out interceptors randomly.
        if game_state.get_resource(MP) >= game_state.type_cost(
                INTERCEPTOR)[MP] and len(deploy_locations) > 0:
            # Choose a random deploy location.
            deploy_index = random.randint(0, len(deploy_locations) - 1)
            deploy_location = deploy_locations[deploy_index]

            game_state.attempt_spawn(INTERCEPTOR, deploy_location)
            """
            We don't have to remove the location since multiple mobile 
            units can occupy the same space.
            """

    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []
        # Get the damage estimate each path will take
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy turrets that can attack each location and multiply by turret damage
                damage += len(game_state.get_attackers(
                    path_location, 0)) * gamelib.GameUnit(
                        TURRET, game_state.config).damage_i
            damages.append(damage)

        # Now just return the location that takes the least damage
        return location_options[damages.index(min(damages))]

    def detect_enemy_unit(self,
                          game_state,
                          unit_type=None,
                          valid_x=None,
                          valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (
                            unit_type is None or unit.unit_type == unit_type
                    ) and (valid_x is None or location[0] in valid_x) and (
                            valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def on_action_frame(self, turn_string):
        """
        This is the action frame of the game. This function could be called 
        hundreds of times per turn and could slow the algo down so avoid putting slow code here.
        Processing the action frames is complicated so we only suggest it if you have time and experience.
        Full doc on format of a game frame at in json-docs.html in the root of the Starterkit.
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        events = state["events"]
        breaches = events["breach"]
        for breach in breaches:
            location = breach[0]
            unit_owner_self = True if breach[4] == 1 else False
            # When parsing the frame data directly,
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if not unit_owner_self:
                gamelib.debug_write("Got scored on at: {}".format(location))
                self.scored_on_locations.append(location)
                gamelib.debug_write("All locations: {}".format(
                    self.scored_on_locations))


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
