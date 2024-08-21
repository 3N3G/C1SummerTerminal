import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from gamelib import GameState
from simulator import Simulator
import copy
from collections import Counter

SPAWNING_LOCATIONS = [[0, 13], [1, 12], [2, 11], [3, 10], [4, 9], [5, 8], [6, 7], [7, 6], [8, 5], [9, 4], [10, 3], [11, 2], [12, 1], [13, 0], [14, 0], [15, 1], [16, 2], [17, 3], [18, 4], [19, 5], [20, 6], [21, 7], [22, 8], [23, 9], [24, 10], [25, 11], [26, 12], [27, 13]]
ENEMY_SPAWNING_LOCATIONS = [[13, 27], [14, 27], [12, 26], [15, 26], [11, 25], [16, 25], [10, 24], [17, 24], [9, 23], [18, 23], [8, 22], [19, 22], [7, 21], [20, 21], [6, 20], [21, 20], [5, 19], [22, 19], [4, 18], [23, 18], [3, 17], [24, 17], [2, 16], [25, 16], [1, 15], [26, 15], [0, 14], [27, 14]]

class Optimizer:
	def __init__(self, initial_board_state, hparams):
		self.initial_board_state = initial_board_state
		self.danger_zone_priority = {
			"LL" : [[4, 13], [4, 12], [0, 13], [3, 13], [3, 12],  [1, 13], [2, 13], [2, 12],  [3, 11], [4, 11], [5, 13], [5, 12], [5, 11]],
			"L" : [[4, 13], [4, 12], [10, 13], [10, 12], [5, 13], [5, 12], [9, 13], [9, 12], [5, 11], [9, 11], [4, 11], [10, 11]],
			"M" : [[10, 13], [10, 12], [17, 13], [17, 12], [11, 13], [11, 12], [16, 13], [16, 12], [11, 11], [16, 11], [10, 11], [17, 11]],
			"R" : [[17, 13], [17, 12], [23, 13], [23, 12], [18, 13], [18, 12], [22, 13], [22, 12], [18, 11], [22, 11], [17, 11], [23, 11]],
			"RR" : [[23, 13], [23, 12], [27, 13], [24, 13], [24, 12], [26, 13], [25, 13], [25, 12],  [24, 11], [23, 11], [22, 13], [22, 12], [22, 11]]
		}
		self.hparams = hparams
		# "LL" : [[4, 13], [4, 12], [3, 13], [3, 12], [0, 13], [1, 13], [2, 13],   [4, 11], [5, 13], [5, 12], [5, 11]],
		# "L" : [[4, 13], [4, 12], [10, 13], [10, 12], [5, 13], [5, 12], [9, 13], [9, 12], [4, 11], [9, 11], [5, 11], [10, 11]],
		# "M" : [[10, 13], [10, 12], [17, 13], [17, 12], [11, 13], [11, 12], [16, 13], [16, 12], [11, 11], [16, 11], [10, 11], [17, 11]],
		# "R" : [[17, 13], [17, 12], [23, 13], [23, 12], [22, 13], [22, 12], [18, 13], [18, 12], [22, 11], [18, 11], [23, 11], [17, 11]],
		# "RR" : [[23, 13], [23, 12], [24, 13], [24, 12], [27, 13], [26, 13], [25, 13],  [25, 12], [24, 11], [23, 11], [22, 13], [22, 12], [22, 11]]

		# self.support_priority = [[14, 1], [13, 2], [12, 3], [11, 4], [10, 5], [9, 6], [8, 7], [7, 8], [6, 9], [15, 1], [14, 2], [13, 3], [12, 4], [11, 5], [10, 6], [9, 7], [8, 8], [15, 2], [14, 3], [13, 4], [12, 5], [11, 6], [10, 7], [9, 8], [7, 9], [8, 9]]

	def optimize_offense(self): # Returns the optimal location and unit for a scout/demo swarm. Returns None if no good move
		best = self.hparams["best"]
		bestloc = None
		shieldloc = None

		num_scouts = int(self.initial_board_state.get_resource(1))

		if num_scouts > self.hparams["minscouts"]:
			best = 0

		for loc in SPAWNING_LOCATIONS:
			if self.initial_board_state.contains_stationary_unit(loc): continue
			# for self_destruct in range(allow_sd + 1):
			new_state = copy.deepcopy(self.initial_board_state)

			for offset in [[-1, -2], [0, -2], [1, -2], [1, -1], [-1, -1],  [0, -1], [-2, -1], [2, -1], [2, 0], [-2, 0], [-1, 0], [1, 0], [-1, 1], [0, 1], [1, 1], [-2, 1], [2, 1], [-1, 2], [0, 2], [1, 2]]:
				val = [offset[0] + loc[0], offset[1] + loc[1]]
				if val[1] > 13: continue
				if not self.initial_board_state.game_map.in_arena_bounds(val): continue
				if self.initial_board_state.contains_stationary_unit(val): continue
				break
			
			new_state.unsafe_spawn("PI", loc, num=num_scouts)

			new_state.unsafe_spawn("EF", val)

			# if self_destruct: new_state.unsafe_spawn("DF", [5, 10])

			PD, SPD, SPD2, _, _, _ = Simulator(new_state).simulate()
			# print(loc, PD, SPD, SPD2)
			score = PD * self.hparams["attack_(s)pdratio"] + SPD #- self_destruct
			if (PD > 0 or SPD > 3) and score > best:
				best = score
				bestloc = loc
				shieldloc = val
				# sding = self_destruct

		return bestloc, shieldloc

	def optimize_defense_mandatory(self, sp, force_upgrade_turrets=True):
		actions = []

		sim = Simulator(self.initial_board_state)

		if force_upgrade_turrets:
			if sp >= 5:
				for turret in sim.turrets:
					if turret.unit.player_index == 0 and turret.unit.upgraded == False:
						actions.append(("UPG", [turret.unit.x, turret.unit.y]))
						sp -= 5
					if sp < 5: break

		for wall in sim.walls:
			if wall.unit.upgraded and wall.unit.health <= 30:
				actions.append(("REMOVE", [wall.unit.x, wall.unit.y]))

		return actions

	def optimize_defense_batch(self, sp, force_upgrade_turrets=True):
		actions = []

		num_attackers = int(self.initial_board_state.get_resource(1, player_index=1))

		danger, best_paths, walls_in_danger = self.compute_danger(self.initial_board_state, num_attackers)
		# print(danger, best_paths)

		if sp >= 2:
			for wall in walls_in_danger:
				actions.append(("UPG", wall))
				sp -= 2
				if sp < 2: break

	
		# Now that all necessary actions are done
		if danger <= self.hparams["mindanger"]:
			return actions 

		priorities = dict()
		for path in best_paths:
			for i in range(len(self.danger_zone_priority[path])):
				if self.initial_board_state.contains_stationary_nonsupport_unit(self.danger_zone_priority[path][i], force_upgrade_turrets):
					continue
				priorities[path] = i
				break


		# print("PRIO: ", priorities)

		added = set()
		while len(priorities) > 0:
			path = min(priorities, key=priorities.get)
			i = priorities[path]
			while len(priorities) > 0 and (self.initial_board_state.contains_stationary_nonsupport_unit(self.danger_zone_priority[path][i], force_upgrade_turrets) or tuple(self.danger_zone_priority[path][i]) in added) :
				priorities[path] += 1
				if priorities[path] >= len(self.danger_zone_priority[path]):
					del priorities[path]
				if len(priorities) == 0: break
				path = min(priorities, key=priorities.get)
				i = priorities[path]

			if len(priorities) == 0: break

			if not force_upgrade_turrets:
				if self.initial_board_state.contains_stationary_unit(self.danger_zone_priority[path][i]) and self.initial_board_state.game_map[self.danger_zone_priority[path][i][0], self.danger_zone_priority[path][i][1]][0].unit_type == "DF":
					if sp >= 5:
						actions.append(("UPG", self.danger_zone_priority[path][i]))
						sp -= 5
					else:
						break

			elif self.danger_zone_priority[path][i][1] == 13:
				if sp >= 2:
					actions.append(("FF", self.danger_zone_priority[path][i]))
					sp -= 2
				else:
					break
			else:
				if sp >= 3:
					actions.append(("DF", self.danger_zone_priority[path][i]))
					sp -= 3

					if sp >= 5:
						actions.append(("UPG", self.danger_zone_priority[path][i]))
						sp -= 5
					else:
						break
				else:
					break

			priorities[path] += 1
			if priorities[path] >= len(self.danger_zone_priority[path]):
					del priorities[path]
			added.add(tuple(self.danger_zone_priority[path][i]))

		return actions


	# def optimize_support(self):
	# 	sp = self.initial_board_state.get_resource(0)
	# 	actions = []
	# 	if sp >= 4:
	# 		for loc in self.support_priority:
	# 			if self.initial_board_state.contains_stationary_unit(loc):
	# 				if loc[1] >= 7 and not self.initial_board_state.game_map[loc[0], loc[1]][0].upgraded:
	# 					actions.append(("UPG", loc))
	# 					sp -= 4
	# 					if sp < 4: break
	# 				continue
	# 			actions.append(("EF", loc))
	# 			sp -= 4
	# 			if sp < 4: break

	# 	return actions



	# def optimize_defense(self):
	# 	num_scouts = int(self.initial_board_state.get_resource(1, player_index=1))

	# 	sp = self.initial_board_state.get_resource(0)
	# 	mp = self.initial_board_state.get_resource(1)

	# 	actions = self.optimize_defense_state(self.initial_board_state, num_scouts, sp, mp)

	# 	return actions


	# def optimize_defense_state(self, substate, num, sp, mp):

	# 	gamelib.debug_write("AAAAAAAAAAAAAAAAAAAAAAAAA")

	# 	danger, attack_loc = self.compute_danger(self.initial_board_state, num)
		
	# 	if danger < 5: return []

	# 	if sp >= 8:
	# 		best_danger = float("inf")
	# 		best_substate = None
	# 		bestloc = None

	# 		for loc in substate.game_map:
	# 			if loc[1] > 13 or substate.contains_stationary_unit(loc): continue

	# 			new_state = copy.deepcopy(substate)

	# 			new_state.unsafe_spawn("DF", loc)
	# 			new_state.unsafe_upgrade(loc)

	# 			new_danger = self.compute_danger_loc(new_state, attack_loc, num)

	# 			if new_danger < best_danger:
	# 				best_danger = new_danger
	# 				bestloc = loc
	# 				best_substate = new_state

	# 		if bestloc == None: return []
	# 		return [("DF", bestloc)] + self.optimize_defense_state(best_substate, num, sp-8, mp)

	# 	if mp >= 2:
	# 		best_danger = float("inf")
	# 		best_substate = None
	# 		bestloc = None

	# 		for loc in SPAWNING_LOCATIONS:
	# 			if not substate.can_spawn("SI", loc): continue

	# 			new_state = copy.deepcopy(substate)

	# 			new_state.unsafe_spawn("SI", loc)

	# 			new_danger, _ = self.compute_danger_loc(new_state, attack_loc, num)

	# 			if new_danger < best_danger:
	# 				best_danger = new_danger
	# 				bestloc = loc
	# 				best_substate = new_state

	# 		if bestloc == None: return []
	# 		return [("SI", bestloc)] + self.optimize_defense_state(best_substate, num, sp, mp-2)

	# 	return []

	def compute_danger(self, substate, num):
		danger = 0
		best_paths = set()
		walls_in_danger = []
		best_values = []
		for loc in ENEMY_SPAWNING_LOCATIONS:
			if self.initial_board_state.contains_stationary_unit(loc): continue
			for unit in ["PI"]:
				new_state = copy.deepcopy(substate)
				
				new_state.unsafe_spawn(unit, loc, num=num, player=1)
				for unit in new_state.game_map[loc[0], loc[1]]:
					unit.health += 3
				
				PD, SPD, SPD2, walls_destroyed, route, values = Simulator(new_state).simulate()
				walls_in_danger += walls_destroyed

				score = PD * self.hparams["defend_(s)pdratio"] + SPD
				if score > danger:
					danger = score
					best_paths = {route}
					best_values = [values]
				if score == danger:
					best_paths.add(route)
					best_values.append(values)

		# gamelib.debug_write(danger, best_values, best_paths)
		return danger, best_paths, walls_in_danger

	# def compute_danger_loc(self, substate, loc, num):
	# 	if self.initial_board_state.contains_stationary_unit(loc): return 0
	# 	for unit in ["PI"]:
	# 		new_state = copy.deepcopy(substate)
			
	# 		new_state.unsafe_spawn(unit, loc, num=num)
			
	# 		PD, SPD, SPD2, path_locations = Simulator(new_state).simulate()
			
	# 		score = PD * 3 + (SPD + SPD2)/2

	# 		gamelib.debug_write(f"running simulation on location {loc}")
	# 	return score



	# def optimize_defense(self):
	# 	sp = int(self.initial_board_state.get_resource(0))

	# 	return self.optimize_defense_substate(copy.deepcopy(self.initial_board_state), sp)

	# def optimize_defense_substate(self, substate, sp):
	# 	if sp < 8: return []

	# 	num_scouts = int(substate.get_resource(1, player_index=1))

	# 	most_dangerous_score = 5
	# 	most_dangerous_loc = None
	# 	most_dangerous_path = None

	# 	danger = dict()

	# 	for loc in ENEMY_SPAWNING_LOCATIONS:
	# 		if substate.contains_stationary_unit(loc): continue
	# 		for unit in ["PI"]:
	# 			new_state = copy.deepcopy(substate)
				
	# 			new_state.unsafe_spawn(unit, loc, num=num_scouts, player=1)

	# 			PD, SPD, SPD2, path_locations = Simulator(new_state).simulate()
	# 			score = PD * 3 + SPD/2
	# 			if score > 5:
	# 				for loc in path_locations:
	# 					if loc not in danger or danger[loc] < score:
	# 						danger[loc] = score

	# 				if score > most_dangerous_score:
	# 					most_dangerous_score = score
	# 					most_dangerous_loc = loc 
	# 					most_dangerous_path = path_locations

	# 	if most_dangerous_loc is None or len(most_dangerous_path) == 0: return []

	# 	gamelib.debug_write("THE MOST DANGEROUS PATH: " + str(most_dangerous_path))

	# 	final_loc = random.choice(most_dangerous_path)

	# 	substate.unsafe_spawn("DF", final_loc)

	# 	return [("DF", final_loc)] + self.optimize_defense_substate(substate, sp-8)


