import random
import json
import subprocess
import os
import shutil
import time
from typing import List, Dict, Tuple
from collections import Counter
from tqdm import tqdm
import itertools

BASE_PARAMS = {
    "best": 8,
    "minscouts": 13,
    "attack_(s)pdratio": 6,
    "mindanger": 4,
    "defend_(s)pdratio": 2,
    "starting_turrets": [
        [
            4,
            12
        ],
        [
            23,
            12
        ],
        [
            10,
            12
        ],
        [
            17,
            12
        ]
    ],
    "starting_wall_x1": 4,
    "starting_wall_y1": 13,
    "starting_wall_x2": 23,
    "starting_wall_y2": 13,
    "min_mp_to_save_sp": 5,
    "min_attack_mp": 8
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
    params["starting_wall_x1"] = random.randint(1, 7)
    params["starting_wall_y1"] = random.randint(12, 14)
    params["starting_wall_x2"] = random.randint(20, 27)
    params["starting_wall_y2"] = random.randint(12, 14)
    return params

def create_algo_folder(params: Dict, folder_name: str):
    os.makedirs(folder_name, exist_ok=True)
    shutil.copytree('python_algo_template', folder_name, dirs_exist_ok=True)
    with open(f'{folder_name}/algo_strategy.py', 'r') as f:
        content = f.read()
    content = content.replace('self.hparams = {}', f'self.hparams = {json.dumps(params, indent=4)}')
    with open(f'{folder_name}/algo_strategy.py', 'w') as f:
        f.write(content)
    
    # Save hyperparameters in a separate file
    with open(f'{folder_name}/hyperparameters.json', 'w') as f:
        json.dump(params, f, indent=4)

def run_game(algo1: str, algo2: str) -> int:
    # Clear the replays folder
    replays_folder = 'replays'
    if os.path.exists(replays_folder):
        for file in os.listdir(replays_folder):
            file_path = os.path.join(replays_folder, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
    else:
        os.makedirs(replays_folder)

    replay_dir = f'completed_replays_{algo1}_{algo2}'
    os.makedirs(replay_dir, exist_ok=True)
    
    # Copy hyperparameters to the replay directory
    shutil.copy(f'{algo1}/hyperparameters.json', f'{replay_dir}/{algo1}_hyperparameters.json')
    shutil.copy(f'{algo2}/hyperparameters.json', f'{replay_dir}/{algo2}_hyperparameters.json')
    
    # Run the game
    subprocess.run(['python', 'scripts/run_match.py', algo1, algo2], check=True)
    
    # Wait for the replay file to be generated
    timeout = 60  # Adjust this value based on how long games typically take
    start_time = time.time()
    while time.time() - start_time < timeout:
        replay_files = [f for f in os.listdir(replays_folder) if f.endswith('.replay')]
        if replay_files:
            # Wait a bit more to ensure the file is fully written
            time.sleep(5)
            replay_file = max(replay_files, key=lambda f: os.path.getctime(os.path.join(replays_folder, f)))
            source_path = os.path.join(replays_folder, replay_file)
            destination_path = os.path.join(replay_dir, replay_file)
            shutil.move(source_path, destination_path)
            with open(destination_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='ignore')
            return 2 if '"winner":2' in content else 1
        time.sleep(1)  # Check every second
    
    raise TimeoutError("Game did not complete within the expected time")

def tournament(population: List[Dict]) -> List[Tuple[Dict, int]]:
    tournament_size = len(population)
    total_games = (tournament_size * (tournament_size - 1)) // 2
    wins = [0] * tournament_size
    
    with tqdm(total=total_games, desc="Tournament Progress", leave=False) as pbar:
        for i, j in itertools.combinations(range(tournament_size), 2):
            algo1 = f'temp_algo_{i}'
            algo2 = f'temp_algo_{j}'
            create_algo_folder(population[i], algo1)
            create_algo_folder(population[j], algo2)
            winner = run_game(algo1, algo2)
            wins[i if winner == 1 else j] += 1
            pbar.update(1)
            
            # Clean up temporary folders after each game
            shutil.rmtree(algo1)
            shutil.rmtree(algo2)
    
    return list(zip(population, wins))

def crossover(parent1: Dict, parent2: Dict) -> Dict:
    child = {}
    for key in parent1.keys():
        if isinstance(parent1[key], list):
            child[key] = random.choice([parent1[key], parent2[key]])
        else:
            child[key] = random.choice([parent1[key], parent2[key]])
    return child

def mutate(individual: Dict, mutation_rate: float = 0.1) -> Dict:
    new_individual = individual.copy()
    for key in new_individual:
        if random.random() < mutation_rate:
            if isinstance(new_individual[key], list):
                # For simplicity, we're not mutating the lists. You might want to implement this.
                pass
            else:
                new_individual[key] += random.randint(-2, 2)
                new_individual[key] = max(1, new_individual[key])  # Ensure positive values
                if key[:13] == "starting_wall":
                    new_individual[key] = min(13, new_individual[key]) # Ensure within bounds
    return new_individual

def genetic_algorithm(population_size: int = 20, generations: int = 10) -> Dict:
    population = [generate_random_params() for _ in range(population_size)]
    
    for generation in range(generations):
        print("")
        print(f"Generation {generation + 1}/{generations}")
        
        # Run tournament
        results = tournament(population)
        
        # Sort results by number of wins
        results.sort(key=lambda x: x[1], reverse=True)
        
        # Select the best performing hyperparameters
        best_params, best_wins = results[0]
        
        print(f"Best performing hyperparameters in generation {generation + 1}:")
        print(json.dumps(best_params, indent=2))
        print(f"Wins: {best_wins}")
        
        # Save the current generation's best individual
        with open(f'generation_{generation + 1}_best.json', 'w') as f:
            json.dump({"params": best_params, "wins": best_wins}, f, indent=4)
        
        # Generate new population based on the best performing hyperparameters
        new_population = [best_params]  # Keep the best performing hyperparameters
        
        while len(new_population) < population_size:
            # Create a new set of hyperparameters by mutating the best performing one
            new_individual = mutate(best_params)
            new_population.append(new_individual)
        
        population = new_population
    
    # Final tournament to determine the overall best
    print("Running final tournament...")
    final_results = tournament(population)
    final_results.sort(key=lambda x: x[1], reverse=True)
    best_params, best_wins = final_results[0]
    
    return best_params

if __name__ == "__main__":
    population_size = 5
    generations = 2

    print(f"Starting genetic algorithm with population size {population_size} and {generations} generations.")

    best_params = genetic_algorithm(population_size, generations)
    
    print("Best hyperparameters found:")
    print(json.dumps(best_params, indent=4))

    # Save the final best parameters
    with open('best_hyperparameters.json', 'w') as f:
        json.dump(best_params, f, indent=4)

    print("Hyperparameter optimization complete. Results saved to 'best_hyperparameters.json'")