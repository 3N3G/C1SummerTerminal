import gamelib
import random
import math
import warnings
from sys import maxsize
import json
from gamelib import GameState
import sys

"""
Here's my plan.

All objects on the field interact solely with mobile units. 
That is, no structures interact with structures.

Therefore, we may search a radius around each mobile unit, and use this

Distance calculations are a waste of time, all radii are fixed, and therefore we can
precompute the normalized distances ahead of time.
(e.g. if unit A has a range of 1, we can compute ahead of time the only cells of note are
+[0, 0], +[0, 1], +[1, 0], +[0, -1], +[-1, 0]). 

INIT: 40SP, 5MP

Wall (2SP): is a wall
  - 40hp
  - Upgrade 2SP -> 120hp

Support (4SP): shields a friendly unit up to once
  - 20hp
  - 2.5 range 
  - Awards (1?) shield
  - Upgrade 4SP -> 6 range, 2 shield (Y coord ... ?)

The following are all single target using standard priority order:

Turret (3SP): shoots things
  - 6dmg 
  - 2.5 range
  - 75 hp
  - Upgrade 5SP -> 14dmg 4.5 range

Scout (1SP): player killer
  - 12hp
  - 2 dmg
  - 4.5 range
  - 1 player damage
  - 1 speed

Demolisher (3SP): structure killer
  - 5 hp
  - 8 dmg
  - 4.5 range
  - 2 player damage
  - 1/2 speed

Interceptor (2SP): mobile killer
  - 30hp
  - 20 dmg
  - 3.5 range
  - 1 player damage
  - 1/4 speed
CANNOT TARGET STRUCTURES

PATHING:
  - Destination is the opposite edge from spawnpoint. Otherwise, deepest
  		point closest to target edge.
  - If this is impossible, run to deepest location and self destruct.
  		(range 1.5, damage = hp, destruct happens after attack)
  - Standard optimal pathfinding, recomputed at each step
  - Break ties by switching direction (Priority given to vertical first)
  - Break ties by direction of target edge, break ties by moving right

TURN ORDER:
	SHIELDING
	MOVEMENT and SELF DESTRUCT DMG
	ATTACK
	0HP DEATH
"""

DISTANCES = {
	2.5 :{(0, 1), (1, 2), (2, 1), (0, 0), (1, 1), (2, 0), (0, 2), (1, 0)},
	6 : {(4, 0), (3, 4), (4, 3), (3, 1), (5, 1), (0, 2), (0, 5), (2, 2), (1, 0), (2, 5), (1, 3), (4, 2), (3, 0), (3, 3), (5, 0), (5, 3), (0, 1), (2, 4), (1, 2), (0, 4), (2, 1), (1, 5), (3, 2), (4, 1), (3, 5), (5, 2), (4, 4), (0, 0), (1, 1), (0, 3), (2, 0), (1, 4), (2, 3)},
}

COSTS = {
	"EF" : [4, 4],
	"DF" : [3, 5],
	"FF" : [2, 2],
}

class GameUnitData:
	def __init__(self, unit, id : int, target_edge : list):
		self.unit = unit

		if unit.unit_type == "EF":
			self.shields_given = False # list of ids

		self.target_edge = target_edge
		self.path = []

		self.id = id

	def __hash__(self):
		return self.id

class Simulator:
	def __init__(self, state : gamelib.GameState):
		self.state = state
		self.PLAYER_DMG = 0
		self.SP_DESTROYED = 0
		self.SP_DMG = 0
		self.PATH_LOCATIONS = []
		self.lane_amounts = {"LL" : 0, "L" : 0, "M" : 0, "R" : 0, "RR" : 0}
		self.centers = {"LL" : [2, 12], "L" : [7, 12], "M" : [13.5, 12], "R" : [20, 12], "RR" : [25, 12]}
		self.warmup()

	def warmup(self):
		# TODO Parse game state to get GameUnitData. ID each creature.

		self.scouts = set()
		self.demolishers = set()
		self.interceptors = set()
		self.shields = set()
		self.turrets = set()
		self.walls = set()

		self.modified = True

		self.units_teamed = {0:set(), 1:set()}

		id = 0
		for x in range(27):
			for y in range(27):
				location = [x, y]
				targ = None
				if any([not unit.stationary for unit in self.state.game_map.get_silent(location)]):
					targ = self.state.get_target_edge(location)
					path = self.state.find_path_to_edge(location, target_edge=targ)
					if len(path) > 0: path = path[1:]
				for unit in self.state.game_map.get_silent(location):
					obj = GameUnitData(unit, id, targ)
					if unit.unit_type == "EF":
						self.shields.add(obj)
					elif unit.unit_type == "FF":
						self.walls.add(obj)
					elif unit.unit_type == "DF":
						self.turrets.add(obj)
					elif unit.unit_type == "PI":
						self.scouts.add(obj)
					elif unit.unit_type == "EI":
						self.demolishers.add(obj)
					elif unit.unit_type == "SI": 
						self.interceptors.add(obj)

					self.units_teamed[unit.player_index].add(obj)
					id += 1

					if not unit.stationary:
						self.unit_location = (unit.x, unit.y)
						self.unit_team = unit.player_index
						self.lowest_health = obj
						obj.path = path.copy()

		self.time = 0

		# gamelib.debug_write(f"Shields: {str([str(i.unit) for i in self.shields])}")

		self.attacking_units = self.scouts.union(self.demolishers).union(self.interceptors)
		# gamelib.debug_write(f"Attackers:{str([str(i.unit) for i in self.attacking_units])}")

		self.units = self.attacking_units.union(self.shields).union(self.walls).union(self.turrets)

	def move(self, unit, l1, l2):
		self.state.game_map[l1[0], l1[1]].remove(unit)
		self.state.game_map[l2[0], l2[1]].append(unit)
		unit.x = l2[0]
		unit.y = l2[1]
		self.unit_location = tuple(l2)

	def move_action(self, unit):
		loc = (unit.unit.x, unit.unit.y)
		path = unit.path.pop(0) if len(unit.path) > 0 else None
		# if unit.unit.y <= 13: self.PATH_LOCATIONS.append(loc)
		# if unit.unit.y >= 13 and unit.unit.unit_type != "SI": self.lane = ["LL", "L", "M", "R", "RR"][(unit.unit.x - 3)//7]
		# gamelib.debug_write(loc)
		# gamelib.debug_write([(x, y) for x, y in self.state.game_map.get_edges()[unit.target_edge]])
		if unit.unit.unit_type != "SI":
			for field in self.lane_amounts:
				if (unit.unit.x - self.centers[field][0])**2 + (unit.unit.y - self.centers[field][1])**2 < 25:
					self.lane_amounts[field] += 1
		if path:
			self.move(unit.unit, loc, path)
		elif loc in [(x, y) for x, y in self.state.game_map.get_edges()[unit.target_edge]]:
			unit.unit.health = 0
			self.PLAYER_DMG += 1 if unit.unit.unit_type != "EI" else 2
		elif self.time >= 5:
			hp = unit.unit.health
			for unit2 in self.units_teamed[1-unit.unit.player_index]:
				if abs(unit2.unit.x - unit.unit.x) <= 1 and abs(unit2.unit.y - unit.unit.y) <= 1:
					unit2.health -= hp + (3 if unit.unit.unit_type == "PI" else (10 if unit.unit.unit_type == "SI" else 0))
					if unit2.stationary:
						self.SP_DMG += COSTS[unit2.unit_type][unit2.upgraded] * min(hp, unit2.health) / unit2.max_health
			unit.unit.health = 0
		else:
			unit.unit.health = 0


	def tick(self):
		# Use find_path_to_edge
		for shield in self.shields:
			if shield.shields_given: continue
			if shield.unit.player_index != self.unit_team: continue
			shield_amount = 3
			shield_range = 2.5
			if shield.unit.upgraded: 
				shield_amount = 2 + 0.3 * min(shield.unit.y, 27 - shield.unit.y)
				shield_range = 6
				
			if (abs(self.unit_location[0] - shield.unit.x), abs(self.unit_location[1] - shield.unit.y)) in DISTANCES[shield_range]:
				shield.shields_given = True
				for unit in self.attacking_units:
					unit.unit.health += shield_amount


		for scout in self.scouts:
			self.move_action(scout)


		if self.time%2 == 0:
			for demolisher in self.demolishers:
				self.move_action(demolisher)

			if self.time%4 == 0:
				for interceptor in self.interceptors:
					self.move_action(interceptor)

		target = None
		for unit in self.attacking_units:
			if target is None or target.health <= 0:
				target = self.state.get_target(unit.unit)
			if target is None: break
			hp = target.health
			target.health -= unit.unit.damage_f
			self.SP_DMG += COSTS[target.unit_type][target.upgraded] * min(hp, unit.unit.damage_f) / target.max_health

		if len(self.attacking_units):
			for attacker in self.state.get_attackers(self.unit_location, self.unit_team):
				self.lowest_health.unit.health -= attacker.damage_i
				if self.lowest_health.unit.health <= 0:
					self.attacking_units.remove(self.lowest_health)
					if len(self.attacking_units) == 0:
						self.lowest_health = None
						break
					self.lowest_health = self.attacking_units.pop()
					self.attacking_units.add(self.lowest_health)

		# units_attacked = set()
		# places_checked = set()
		# for unit in self.attacking_units:
		# 	target = self.state.get_target(unit.unit)
		# 	if target:
		# 		hp = target.health
		# 		if target.stationary:
		# 			target.health -= unit.unit.damage_f
		# 			self.SP_DMG += COSTS[target.unit_type][target.upgraded] * min(hp, unit.unit.damage_f) / target.max_health
		# 		else:
		# 			target.health -= unit.unit.damage_i
		# 	tup0 = (unit.unit.x, unit.unit.y, unit.unit.player_index)
		# 	if tup0 not in places_checked:
		# 		places_checked.add(tup0)
		# 		for other_unit in self.state.get_attackers([unit.unit.x, unit.unit.y], unit.unit.player_index):
		# 			tup = (other_unit.x, other_unit.y)
		# 			if tup not in units_attacked:
		# 				units_attacked.add(tup)
		# 				target2 = self.state.get_target(other_unit)
		# 				if target2: target2.health -= unit.unit.damage_i


		self.modified = False
		for unit in self.units.copy():
			if unit.unit.health <= 0:
				if unit.unit.unit_type in COSTS:
					self.SP_DESTROYED += COSTS[unit.unit.unit_type][unit.unit.upgraded]
					self.modified = True
					if unit.unit.unit_type == "FF" and unit.unit.upgraded == False:
						self.PATH_LOCATIONS.append([unit.unit.x, unit.unit.y])
				for S in [self.scouts, self.demolishers, self.interceptors, self.shields, self.turrets, self.walls, self.attacking_units, self.units_teamed[0], self.units_teamed[1], self.units]:
					if unit in S:
						S.remove(unit)
				self.state.game_map[unit.unit.x, unit.unit.y].remove(unit.unit)

		self.time += 1

	def __str__(self):
		s = f"{self.PLAYER_DMG} {self.SP_DESTROYED} {self.SP_DMG} {self.unit_location} {self.unit_team}\n" 
		for unit in self.units:
			s += f"\t{str(unit.unit)}\n"
		return s

	def simulate(self):
		i = 0
		while len(self.scouts) + len(self.interceptors) + len(self.demolishers) > 0:
			i += 1
			if i > 100: gamelib.debug_write("CCCCCCCCCCCCCCCCCCCCCCCC")
			self.tick()
		return (self.PLAYER_DMG, self.SP_DESTROYED, self.SP_DMG, self.PATH_LOCATIONS, max(self.lane_amounts, key = self.lane_amounts.get), self.lane_amounts)

	# def convert(self, unit):
	# 	print(unit, [str(i.unit) for i in self.units])
	# 	for unit_2 in self.units:
	# 		unit2 = unit_2.unit
	# 		if unit.player_index == unit2.player_index and unit.health == unit2.health and unit.unit_type == unit2.unit_type:
	# 			return unit_2
