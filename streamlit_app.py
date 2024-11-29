import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import googlemaps
import requests

# Initialize Google Maps Client with your API key
gmaps = googlemaps.Client(key='AIzaSyCWMQHWmPEF9BSjifnCgAnMhpdqRBpg2Ok')

# Set base constants for energy consumption
base_energy_consumption_rate = 200  # Base energy consumption rate in Wh/km
energy_price_per_kwh_default = 1.5  # Default energy price per kWh in MAD

# Set base constants for energy consumption
base_energy_consumption_rate = 200  # Base energy consumption rate in Wh/km
energy_price_per_kwh_default = 1.5  # Default energy price per kWh in MAD

# Car models and their battery capacities (in kWh)
car_models = {
    'Tesla Model 3': 75,
    'Nissan Leaf': 40,
    'Chevrolet Bolt': 66,
    'Tesla Model S': 100,
    'Hyundai Kona Electric': 64,
    'BMW i3': 42.2,
    'Audi e-tron': 95,
    'Jaguar I-PACE': 90,
    'Ford Mustang Mach-E': 88
}

# Air conditioner consumption rates for different levels
air_conditioner_levels = {
    'Off': 0,      # 0% more consumption
    'Low': 10,     # 10% more consumption
    'Medium': 15,  # 15% more consumption
    'High': 20     # 20% more consumption
}

# Function to fetch weather data using OpenWeatherMap API
def get_weather_data(Morocco):
    weather_api_key = '7cfd90dcf40d723c91222ace2a4128df'
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={Morocco}&appid={weather_api_key}&units=metric"
    response = requests.get(weather_url)
    if response.status_code == 200:
        weather_data = response.json()
        return weather_data['main']['temp']  # Return the temperature in °C
    else:
        return None

# Streamlit app title and description
st.title("Enhanced EV Energy Consumption and Cost Calculator")
st.write("This app calculates the energy consumption and cost for trips in Morocco considering car models, weather, air conditioner usage, and charging stops.")

# User inputs for origin and destination
origin = st.text_input("Enter the origin city (e.g., Ifrane)", "Ifrane, Morocco")
destination = st.text_input("Enter the destination city (e.g., Tangier)", "Tangier, Morocco")

# Select car model
selected_car = st.selectbox("Select your car model", list(car_models.keys()))
battery_capacity_kwh = car_models[selected_car]

# Fetch weather data for the origin city
weather = get_weather_data(origin)
if weather is not None:
    st.write(f"Current temperature in {origin}: {weather}°C")
else:
    st.write("Weather data could not be retrieved. Using default temperature of 25°C.")
    weather = 25  # Use a default temperature if the API fails

# Fetch route options from Google Maps Directions API
routes = []
if origin and destination:
    try:
        directions_result = gmaps.directions(origin, destination, mode="driving", alternatives=True)
        for i, route in enumerate(directions_result):
            route_summary = route['summary']
            distance_km = route['legs'][0]['distance']['value'] / 1000
            duration_hours = route['legs'][0]['duration']['value'] / 3600
            routes.append((route_summary, distance_km, duration_hours))
    except Exception as e:
        st.error("Error fetching data from Google Maps. Please check your input or API key.")
        routes = []

# Let the user choose between available routes
if routes:
    selected_route = st.selectbox("Select a route", [f"{route[0]}: {route[1]:.2f} km, {route[2]:.2f} hours" for route in routes])
    selected_route_data = routes[[f"{route[0]}: {route[1]:.2f} km, {route[2]:.2f} hours" for route in routes].index(selected_route)]
    distance_km = selected_route_data[1]
    duration_hours = selected_route_data[2]

    # Get latitude and longitude from the starting point of the route
    start_location = directions_result[0]['legs'][0]['start_location']
    start_lat = start_location['lat']
    start_lng = start_location['lng']
    
    location_coordinates = (start_lat, start_lng)  # Use these coordinates for places_nearby
else:
    distance_km = 0
    duration_hours = 0

# User input for speed (km/h)
speed = st.slider("Select the average speed (km/h)", min_value=40, max_value=160, value=100, step=10)

# Automatically calculate the duration based on distance and speed if speed changes
if distance_km > 0:
    duration = distance_km / speed

# User input for electricity price per kWh
energy_price_per_kwh = st.slider("Select the price of electricity (MAD per kWh)", min_value=0.5, max_value=3.0, value=energy_price_per_kwh_default, step=0.1)

# Select air conditioner level
air_conditioner_level = st.selectbox("Select air conditioner level", list(air_conditioner_levels.keys()))
air_conditioner_penalty = air_conditioner_levels[air_conditioner_level] / 100  # Convert to fraction

# Function to calculate energy consumption (in kWh)
def calculate_energy_consumption(speed, distance_km, air_conditioner_penalty, weather):
    efficiency_factor = 1 + (speed - 100) / 100  # Assume energy consumption increases with speed
    energy_consumed_wh = (distance_km * base_energy_consumption_rate) / efficiency_factor

    # Adjust for air conditioner usage
    energy_consumed_wh *= 1 + air_conditioner_penalty
    
    # Adjust for hot weather if temperature is above 30°C
    if weather > 30:
        energy_consumed_wh *= 1.15  # 15% extra consumption for hot weather

    energy_consumed_kwh = energy_consumed_wh / 1000  # Convert Wh to kWh
    return energy_consumed_kwh

# Function to calculate total cost
def calculate_total_cost(energy_consumed_kwh, energy_price_per_kwh):
    return energy_consumed_kwh * energy_price_per_kwh

# Perform calculations if distance is available
if distance_km > 0:
    energy_consumed_kwh = calculate_energy_consumption(speed, distance_km, air_conditioner_penalty, weather)
    total_cost = calculate_total_cost(energy_consumed_kwh, energy_price_per_kwh)

    # Check if the battery can handle the trip without recharging
    if energy_consumed_kwh > battery_capacity_kwh:
        st.write(f"⚠️ The trip will require recharging! Your car's battery capacity is {battery_capacity_kwh} kWh, but the trip requires {energy_consumed_kwh:.2f} kWh.")
        
        # Calculate how many charging stops are needed
        recharge_stops = int(energy_consumed_kwh // battery_capacity_kwh)
        remaining_energy = energy_consumed_kwh % battery_capacity_kwh
        
        # Only add an extra stop if remaining energy is more than 0
        if remaining_energy > 0:
            recharge_stops += 1
        
        st.write(f"You will need to stop {recharge_stops} times for recharging.")
        
        # Use the correct location for finding nearby charging stations
        charging_stations = gmaps.places_nearby(location=location_coordinates, radius=50000, type='electric_vehicle_charging_station')
        if charging_stations['results']:
            st.write("Suggested charging stations along your route:")
            for station in charging_stations['results']:
                st.write(f"- {station['name']} at {station['vicinity']}")
        else:
            st.write("No charging stations found along your route.")
    else:
        st.write(f"✅ The trip can be completed without recharging. Your car's battery capacity is {battery_capacity_kwh} kWh, and the trip requires {energy_consumed_kwh:.2f} kWh.")

    # Display the results
    st.write(f"### Trip Information:")
    st.write(f"- Distance: {distance_km:.2f} km (via {selected_route_data[0]})")
    st.write(f"- Average Speed: {speed} km/h")
    st.write(f"- Trip Duration: {duration:.2f} hours")

    st.write(f"### Energy Consumption and Cost:")
    st.write(f"The estimated energy consumption for this trip is **{energy_consumed_kwh:.2f} kWh**.")
    st.write(f"The estimated total cost of the energy consumed is **{total_cost:.2f} MAD** (at {energy_price_per_kwh} MAD per kWh).")

else:
    st.write("Enter valid cities for origin and destination to calculate the distance and energy consumption.")
