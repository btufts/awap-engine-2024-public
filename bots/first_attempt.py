from src.player import Player
from src.map import Map
from src.robot_controller import RobotController
from src.game_constants import TowerType, Team, Tile, GameConstants, SnipePriority, get_debris_schedule
from src.debris import Debris
from src.tower import Tower
import numpy as np

import sys

class DevNull:
    def write(self, msg):
        pass

sys.stderr = DevNull()

class BotPlayer(Player):
    def __init__(self, map: Map):
        self.map = map
        self.shooter_positions, self.solar_positions, self.score_map = self.calc_scores()
        self.reinforcer_positions = []

        self.solar_panel = 0


        # np.set_printoptions(linewidth=150)
        # print(np.matrix(np.array(self.score_map)))
        # print(*self.positions)

        # exit()
    
    def calc_scores(self):
        score_map = [[0 for _ in range(self.map.width)] for _ in range(self.map.height)]

        curr_score = 50000

        q = []
        visited = set()
        for x,y in self.map.path:
            if (x+1,y) not in visited and self.map.is_space(x+1,y):
                score_map[y][x+1] += curr_score
                q.append((x+1, y))
            if (x-1,y) not in visited and self.map.is_space(x-1,y):
                score_map[y][x-1] += curr_score
                q.append((x-1, y))
            if (x,y+1) not in visited and self.map.is_space(x,y+1):
                score_map[y+1][x] += curr_score
                q.append((x, y+1))
            if (x,y-1) not in visited and self.map.is_space(x,y-1):
                score_map[y-1][x] += curr_score
                q.append((x, y-1))

            if (x+1,y+1) not in visited and self.map.is_space(x+1,y+1):
                score_map[y+1][x+1] += curr_score
                q.append((x+1, y+1))
            if (x+1,y-1) not in visited and self.map.is_space(x+1,y-1):
                score_map[y-1][x+1] += curr_score
                q.append((x+1, y-1))
            if (x-1,y+1) not in visited and self.map.is_space(x-1,y+1):
                score_map[y+1][x-1] += curr_score
                q.append((x-1, y+1))
            if (x-1,y-1) not in visited and self.map.is_space(x-1,y-1):
                score_map[y-1][x-1] += curr_score
                q.append((x-1, y-1))

            curr_score += 100

        total_space = 0

        while len(q) != 0:
            x,y = q.pop()
            visited.add((x,y))
            new_score = score_map[y][x] // 50
            if self.map.is_space(x+1,y):
                total_space += 1
                score_map[y][x+1] += new_score
                if (x+1,y) not in visited: 
                    q.append((x+1, y))
            if self.map.is_space(x-1,y):
                total_space += 1
                score_map[y][x-1] += new_score
                if (x-1,y) not in visited:
                    q.append((x-1, y))
            if self.map.is_space(x,y+1):
                total_space += 1
                score_map[y+1][x] += new_score
                if (x,y+1) not in visited:
                    q.append((x, y+1))
            if self.map.is_space(x,y-1):
                total_space += 1
                score_map[y-1][x] += new_score
                if (x,y-1) not in visited:
                    q.append((x, y-1))

            if self.map.is_space(x+1,y+1):
                score_map[y+1][x+1] += new_score
                if (x+1,y+1) not in visited: 
                    q.append((x+1, y+1))
            if self.map.is_space(x+1,y-1):
                score_map[y-1][x+1] += new_score
                if (x+1,y-1) not in visited:
                    q.append((x+1, y-1))
            if (x-1,y+1) not in visited and self.map.is_space(x-1,y+1):
                score_map[y+1][x-1] += new_score
                if (x-1,y+1) not in visited:
                    q.append((x-1, y+1))
            if (x-1,y-1) not in visited and self.map.is_space(x-1,y-1):
                score_map[y-1][x-1] += new_score
                if (x-1,y-1) not in visited:
                    q.append((x-1, y-1))

        scores = []
        solar_scores = []
        score_map = np.flipud(np.array(score_map))
        for i in range(self.map.height):
            for j in range(self.map.width):
                if score_map[i][j] > 10000 and len(scores):
                    scores.append((score_map[i][j], (j,self.map.height-1-i)))
                else:
                    solar_scores.append((score_map[i][j], (j,self.map.height-1-i)))

        return sorted(scores), sorted(solar_scores), score_map
    
    def tower_action(self, me, enemy, rc):
        towers = rc.get_towers(me)
        for tower in towers:
            # debris_in_range = rc.sense_debris_within_radius_squared(me, tower.x, tower.y, tower.type.range)
            match tower.type:
                case TowerType.BOMBER:
                    rc.auto_bomb(tower.id)
                case TowerType.GUNSHIP:
                    rc.auto_snipe(tower.id, SnipePriority.STRONG)
                case TowerType.REINFORCER:
                    pass
                case TowerType.SOLAR_FARM:
                    pass

    def play_turn(self, rc: RobotController):

        me = rc.get_ally_team()
        enemy = rc.get_enemy_team()

        my_energy = rc.get_balance(me)
        enemy_energy = rc.get_balance(enemy)

        towers = rc.get_towers(me)

        if self.solar_panel == 5:
            _, (x,y) = self.solar_positions[len(self.solar_positions)-1]
            if rc.can_build_tower(TowerType.SOLAR_FARM, x, y):
                self.solar_panel = 0
                self.solar_positions.pop()
                rc.build_tower(TowerType.SOLAR_FARM, x, y)
        elif len(towers) > 5 and len(self.reinforcer_positions) > 2:
            (x,y) = self.reinforcer_positions[0]
            if rc.can_build_tower(TowerType.REINFORCER, x, y):
                self.reinforcer_positions.pop(0)
                rc.build_tower(TowerType.REINFORCER, x, y)
        else:
            s, (x, y) = self.shooter_positions[len(self.shooter_positions)-1]
            
            if s > 200000:
                if rc.can_build_tower(TowerType.BOMBER, x, y):
                    self.shooter_positions.pop()
                    rc.build_tower(TowerType.BOMBER, x, y)
                    self.solar_panel += 1
                    for (x,y) in [(x+1,y+1), (x+1,y-1), (x-1,y+1), (x-1,y-1)]:
                        if self.map.is_space(x,y):
                            self.reinforcer_positions.append((x,y))
                            try:
                                self.shooter_positions.remove((x,y))
                            except(ValueError):
                                pass
                            break
            else:
                if rc.can_build_tower(TowerType.GUNSHIP, x, y):
                    self.solar_panel += 1
                    self.shooter_positions.pop()
                    rc.build_tower(TowerType.GUNSHIP, x, y)

        self.tower_action(me, enemy, rc)
        
        return