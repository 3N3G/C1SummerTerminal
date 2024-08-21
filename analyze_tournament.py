import os
import re
import json
from collections import defaultdict

def parse_replay(replay_file):
    with open(replay_file, 'rb') as f:
        content = f.read().decode('utf-8', errors='ignore')
    
    winner_match = re.search(r'"winner":(\d)', content)
    if winner_match:
        return int(winner_match.group(1))
    return None

def extract_hyperparameters(algo_folder):
    algo_strategy_path = os.path.join(algo_folder, 'algo_strategy.py')
    if os.path.exists(algo_strategy_path):
        with open(algo_strategy_path, 'r') as f:
            content = f.read()
            hparams_match = re.search(r'self\.hparams\s*=\s*(\{[^}]+\})', content, re.DOTALL)
            if hparams_match:
                return eval(hparams_match.group(1))
    return None

def analyze_tournament(base_folder):
    results = defaultdict(lambda: {'wins': 0, 'losses': 0, 'hparams': None})
    replay_folders = [f for f in os.listdir(base_folder) if f.startswith('completed_replays_')]
    
    for replay_folder in replay_folders:
        print(f"REPLAY FOLDER {replay_folder}")
        match = re.match(r'completed_replays_temp_algo_(\d)_temp_algo_(\d)', replay_folder)
        if match:
            algo1, algo2 = match.groups()
            # List all .replay files in the directory
            replay_files = [f for f in os.listdir(os.path.join(base_folder, replay_folder)) if f.endswith('.replay')]

            # Check if there are any .replay files and get the first one
            if replay_files:
                replay_file = os.path.join(base_folder, replay_folder, replay_files[0])
            else:
                replay_file = None  # Or handle the case where no .replay files are found
            
            print("REPLAY FILE", replay_file)
            winner = parse_replay(replay_file)
            
            if winner == 1:
                results[f'temp_algo_{algo1}']['wins'] += 1
                results[f'temp_algo_{algo2}']['losses'] += 1
            elif winner == 2:
                results[f'temp_algo_{algo2}']['wins'] += 1
                results[f'temp_algo_{algo1}']['losses'] += 1
    
    # Extract hyperparameters for each algorithm
    for algo in results.keys():
        algo_folder = os.path.join(base_folder, algo)
        if os.path.exists(algo_folder):
            results[algo]['hparams'] = extract_hyperparameters(algo_folder)
    
    return results

def main():
    base_folder = '.'  # Assuming the script is run from the folder containing all algo and replay folders
    results = analyze_tournament(base_folder)
    
    # Find the best performing algorithm
    best_algo = max(results, key=lambda x: results[x]['wins'])
    
    print(f"Best performing algorithm: {best_algo}")
    print(f"Wins: {results[best_algo]['wins']}")
    print(f"Losses: {results[best_algo]['losses']}")
    print("Hyperparameters:")
    print(json.dumps(results[best_algo]['hparams'], indent=2))
    
    print("\nAll results:")
    for algo, data in sorted(results.items(), key=lambda x: x[1]['wins'], reverse=True):
        print(f"{algo}: Wins - {data['wins']}, Losses - {data['losses']}")
    
    # Save detailed results to a file
    with open('tournament_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\nDetailed results saved to 'tournament_results.json'")

if __name__ == "__main__":
    main()
