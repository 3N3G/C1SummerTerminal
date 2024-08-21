import random
import json
import subprocess
import os
import shutil
import time
from typing import List, Dict, Tuple
from collections import Counter
from tqdm import tqdm

BASE_PARAMS = {
    "best": 5,
    "minscouts": 12,
    "attack_(s)pdratio": 4,
    "mindanger": 2,
    "defend_(s)pdratio": 3,
    "starting_turrets": [[4, 12], [23, 12], [10, 12], [17, 12]],
    "starting_walls": [[4, 13], [23, 13]],
    "min_mp_to_save_sp": 10,
    "min_attack_mp": 10
}

def generate_random_params() -> Dict:
    params = BASE_PARAMS.copy()
    params["best"] = random.randint(3, 8)
    params["minscouts"] = random.randint(8, 16)
    params["attack_(s)pdratio"] = random.randint(2, 6)
    params["mindanger"] = random.randint(1, 4)
    params["defend_(s)pdratio"] = random.randint(2, 5)
    params["min_mp_to_save_sp"] = random.randint(5, 15)
    params["min_attack_mp"] = random.randint(5, 15)
    return params

def create_algo_folder(params: Dict, folder_name: str):
    os.makedirs(folder_name, exist_ok=True)
    shutil.copytree('python_algo_template', folder_name, dirs_exist_ok=True)
    with open(f'{folder_name}/algo_strategy.py', 'r') as f:
        content = f.read()
    content = content.replace('self.hparams = {}', f'self.hparams = {json.dumps(params, indent=4)}')
    with open(f'{folder_name}/algo_strategy.py', 'w') as f:
        f.write(content)

def run_game(algo1: str, algo2: str) -> int:
    # Remove old replay files
    for file in os.listdir('replays'):
        os.remove(os.path.join('replays', file))
    
    # Run the game
    subprocess.run(['python', 'scripts/run_match.py', algo1, algo2], check=True)
    
    # Wait for the replay file to be generated
    timeout = 90  # Adjust this value based on how long games typically take
    start_time = time.time()
    while time.time() - start_time < timeout:
        replay_files = os.listdir('replays')
        if replay_files:
            # Wait a bit more to ensure the file is fully written
            time.sleep(5)
            replay_file = max(replay_files, key=lambda f: os.path.getctime(os.path.join('replays', f)))
            with open(os.path.join('replays', replay_file), 'r') as f:
                content = f.read()
            winner = 2 if '"winner":2' in content else 1
            
            # Move the replay file to a unique location
            new_replay_dir = f'completed_replays_{algo1}_{algo2}'
            os.makedirs(new_replay_dir, exist_ok=True)
            shutil.move(os.path.join('replays', replay_file), os.path.join(new_replay_dir, replay_file))
            
            return winner
        time.sleep(1)  # Check every second
    
    raise TimeoutError("Game did not complete within the expected time")

def tournament(population: List[Dict], tournament_size: int = 5) -> Dict:
    tournament = random.sample(population, tournament_size)
    winners = []
    total_games = (tournament_size * (tournament_size - 1)) // 2
    with tqdm(total=total_games, desc="Tournament Progress", leave=False) as pbar:
        for i in range(len(tournament)):
            for j in range(i+1, len(tournament)):
                algo1 = f'temp_algo_{i}'
                algo2 = f'temp_algo_{j}'
                create_algo_folder(tournament[i], algo1)
                create_algo_folder(tournament[j], algo2)
                winner = run_game(algo1, algo2)
                winners.append(i if winner == 1 else j)
                shutil.rmtree(algo1)
                shutil.rmtree(algo2)
                pbar.update(1)
    winner_index = Counter(winners).most_common(1)[0][0]
    return tournament[winner_index]

def crossover(parent1: Dict, parent2: Dict) -> Dict:
    child = {}
    for key in parent1.keys():
        if isinstance(parent1[key], list):
            child[key] = random.choice([parent1[key], parent2[key]])
        else:
            child[key] = random.choice([parent1[key], parent2[key]])
    return child

def mutate(individual: Dict, mutation_rate: float = 0.1) -> Dict:
    for key in individual:
        if random.random() < mutation_rate:
            if isinstance(individual[key], list):
                # For simplicity, we're not mutating the lists. You might want to implement this.
                pass
            else:
                individual[key] += random.randint(-2, 2)
                individual[key] = max(1, individual[key])  # Ensure positive values
    return individual

def genetic_algorithm(population_size: int = 5, generations: int = 3) -> Tuple[Dict, float]:
    population = [generate_random_params() for _ in range(population_size)]
    
    for generation in tqdm(range(generations), desc="Generations"):
        new_population = []
        
        # Elitism: keep the best individual
        best = tournament(population, tournament_size=len(population))
        new_population.append(best)
        
        with tqdm(total=population_size-1, desc="Creating New Population", leave=False) as pbar:
            while len(new_population) < population_size:
                parent1 = tournament(population)
                parent2 = tournament(population)
                child = crossover(parent1, parent2)
                child = mutate(child)
                new_population.append(child)
                pbar.update(1)
        
        population = new_population
    
    # Final tournament to determine the best
    print("Running final tournament...")
    best = tournament(population, tournament_size=len(population))
    return best

if __name__ == "__main__":
    best_params = genetic_algorithm()
    print("Best hyperparameters found:")
    print(json.dumps(best_params, indent=4))
    
    # Save the best parameters
    with open('best_hyperparameters.json', 'w') as f:
        json.dump(best_params, f, indent=4)
