#!/bin/bash

# Function to check if all "algo_i" folders exist
all_folders_exist() {
    for i in {0..19}; do
        if [ ! -d "algo_$i" ]; then
            return 1
        fi
    done
    return 0
}

# Loop until all folders "algo_0" to "algo_19" exist
while ! all_folders_exist; do
    for i in {0..19}; do
        if [ -d "temp_algo_$i" ] && [ ! -d "algo_$i" ]; then
            cp -r "temp_algo_$i" "algo_$i"
            echo "Copied temp_algo_$i to algo_$i"
        fi
    done
    sleep 1  # Wait a bit before checking again to prevent tight looping
done

echo "All algo_0 to algo_19 folders now exist. Exiting."

