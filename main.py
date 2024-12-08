import simpy
import random
import matplotlib.pyplot as plt

env = simpy.Environment()

class Station:
    def __init__(self, env, name, capacity, init_bikes):
        self.env = env
        self.name = name
        self.capacity = capacity
        self.bikes = simpy.Container(env, init=init_bikes, capacity=capacity)

# first requierment declaring the 4 stations #
upt_station = Station(env, "UPT", capacity = 16, init_bikes = 6)
center_station = Station(env, "Center", capacity = 10, init_bikes = 5)
piata_700 = Station(env, "Piata700", capacity = 25, init_bikes = 10)
calea_lipovei = Station(env, "Lipovei", capacity = 15, init_bikes = 5)

stations = [upt_station, center_station, piata_700, calea_lipovei]

# Second requierment #
# Time matrixes

time_slots = [
    {
        'name': 'morning_start',
        'start': 0,       # Start of the day (6:00 AM)
        'end': 120,       # 2 hours later (8:00 AM)
        'prob_matrix': {
            (upt_station, center_station): 0.4,
            (center_station, upt_station): 0.6,
            (upt_station, piata_700): 0.2,
            (piata_700, upt_station): 0.5,
            (center_station, piata_700): 0.3,
            (piata_700, center_station): 0.4,
            (upt_station, calea_lipovei): 0.3,
            (calea_lipovei, upt_station): 0.2,
        }
    },
    {
        'name': 'midday',
        'start': 120,     # 2 hours after start (8:00 AM)
        'end': 720,       # Until 6:00 PM
        'prob_matrix': {
            (upt_station, center_station): 0.2,
            (center_station, upt_station): 0.3,
            (upt_station, piata_700): 0.1,
            (piata_700, upt_station): 0.2,
            (center_station, piata_700): 0.25,
            (piata_700, center_station): 0.35,
            (upt_station, calea_lipovei): 0.15,
            (calea_lipovei, upt_station): 0.25,
        }
    }
]

# Default matrix for times outside defined slots
default_prob_matrix = {
    (upt_station, center_station): 0.05,
    (center_station, upt_station): 0.05,
    (upt_station, piata_700): 0.05,
    (piata_700, upt_station): 0.05,
    (center_station, piata_700): 0.05,
    (piata_700, center_station): 0.05,
    (upt_station, calea_lipovei): 0.05,
    (calea_lipovei, upt_station): 0.05,
}

# Function to find the time of day slot we fit in
def get_current_time_slot(minute_of_day):
    for slot in time_slots:
        if slot['start'] <= minute_of_day < slot['end']:
            return slot['prob_matrix']
    return default_prob_matrix

# Defining the Bike Trip Process
# This has not been changed from the original (Lab 3)
def bike_trip(env, from_station, to_station, trip_duration, repair_list):

    global broken_bikes
    global unhappy_customers_empty_station
    global unhappy_customers_broken_bike
    global unhappy_customers_full_station

    if from_station.bikes.level > 0:
        yield from_station.bikes.get(1)
        print(f"Time {env.now}: Bike taken from {from_station.name}")
    else:
        unhappy_customers_empty_station += 1 # Unhappy custommers due to no bikes in station
        print(f"Time {env.now}: No bikes available at {from_station.name}")
        return  # Trip cannot proceed without a bike

    # Simulate the trip duration

    if random.uniform (0, 1) < maintenance_prob:   #Function for third requierment
        print(f"Time {env.now}: Bike failed during trip from {from_station.name} to {to_station.name}")
        broken_bikes += 1
        unhappy_customers_broken_bike += 1 # also unhappy customers due to breaking down of bike
        env.process(repair_bike(env, repair_list, from_station))
        return  #The function stops since the bike broke down

    yield env.timeout(trip_duration)

    if to_station.bikes.level < to_station.capacity:
        yield to_station.bikes.put(1)
        print(f"Time {env.now}: Bike returned to {to_station.name}")
    else:
        unhappy_customers_full_station += 1 # Unhappy customer due to full station on arrival
        print(f"Time {env.now}: No docks available at {to_station.name}, returning bike to {from_station.name}")
        yield env.timeout(trip_duration)
        if from_station.bikes.level > 0:
            yield from_station.bikes.put(1)
            print(f"Time {env.now}: Bike returned to {from_station.name}")
        # For simplicity, the bike is returned to original station - if there are no empty slots, we lose the bike


def generate_trips(env):

    while True:
        # Decide what prob matrix we should use based on the time
        current_minute = env.now % 1440 # 1440 minutes in a day getting the reminder of that tells us how many minutes we are into the simulation
        prob_matrix = get_current_time_slot(current_minute)

        for (from_station, to_station), prob in prob_matrix.items():
            if random.uniform(0, 1) < prob:
                trip_duration = 1  # Fixed trip duration for simplicity
                env.process(bike_trip(env, from_station, to_station, trip_duration, repair_list))
        yield env.timeout(1)  # Wait for 1 minute before checking again

# Third requierment #
maintenance_prob = 0.05
maintenance_time = 15
repair_list = simpy.Resource(env, capacity=2)

broken_bikes = 0

def repair_bike(env, repair_list, station):

    global broken_bikes

    with repair_list.request() as request:
      yield request
      print(f"Time {env.now}: Bike repair started")

      yield env.timeout(maintenance_time)

    if station.bikes.level < station.capacity:
      yield station.bikes.put(1)
      print(f"Time {env.now}: Bike repaired and returned to {station.name}")
    else:
        print(f"Time {env.now}: No space at {station.name} after repair; bike removed from circulation")

    broken_bikes -= 1

# Fourth requierment #

def rebalancing_station(env, stations):
    if env.now % 5 == 0:
          for station in stations:
            if station.bikes.level == station.capacity or station.bikes.level < 2:

              for other_station in stations:
                if other_station != station:
                  yield station.bikes.get(1)
                  yield other_station.bikes.put(1)
                  print(f"Time {env.now}: Bike rebalanced from {station.name} to {other_station.name}")
                  break
    yield env.timeout(1)

# Fifth requierment #

unhappy_customers_empty_station = 0
unhappy_customers_broken_bike = 0
unhappy_customers_full_station = 0

# Sixth requierment and seventh #

def monitor_stations(env, stations, bike_levels):
    while True:
        for station in stations:
            bike_levels[station.name].append((env.now, station.bikes.level))

        unhappy_customers.append((env.now, unhappy_customers_empty_station, unhappy_customers_full_station, unhappy_customers_broken_bike)) # plotting the customers
        broken_bikes_for_plotting.append((env.now, broken_bikes)) # ploting the bikes

        yield env.timeout(1)

# The 3 data structs needed to hold the data for ploting #
bike_levels = {station.name: [] for station in stations}
broken_bikes_for_plotting = []
unhappy_customers = []

# All the main processes that we call #
env.process(generate_trips(env))
env.process(monitor_stations(env, stations, bike_levels))
env.process(rebalancing_station(env, stations))

# Running the Simulation #
env.run(until= 1440)

# Plotting the bike levels over time
plt.figure(figsize=(12, 6))
for station_name, levels in bike_levels.items():
    times, counts = zip(*levels)
    plt.plot(times, counts, label=station_name)

plt.xlabel('Time (minutes)')
plt.ylabel('Number of Bikes')
plt.title('Bike Levels at Each Station Over Time')
plt.legend()
plt.grid(True)
plt.show()

# Visualizing unhappy customers and broken bikes
times_unhappy, empty_counts, full_counts, broken_counts = zip(*unhappy_customers)
times_broken, broken_counts = zip(*broken_bikes_for_plotting)

plt.figure(figsize=(12, 6))

plt.subplot(1, 2, 1)
plt.plot(times_unhappy, empty_counts, label='Unhappy Customers (Empty Station)', color='red')
plt.plot(times_unhappy, full_counts, label='Unhappy Customers (Full Station)', color='orange')
plt.plot(times_unhappy, broken_counts, label='Unhappy Customers (Broken Bike)', color='blue')
plt.xlabel('Time (minutes)')
plt.ylabel('Number of Unhappy Customers')
plt.title('Unhappy Customers Over Time')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(times_broken, broken_counts, label='Broken Bikes', color='blue')
plt.xlabel('Time (minutes)')
plt.ylabel('Number of Broken Bikes')
plt.title('Broken Bikes Over Time')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()