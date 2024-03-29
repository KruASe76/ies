import ips
import json
from statistics import mean
from typing import List


# psm = ips.init()
psm = ips.from_log("logs/logs_2_evening.json", 10)


FILENAME = "chekanshchiki_temp.json"

if psm.tick == 0:
    json_data = {"market": [0] * 101}
else:
    with open(FILENAME, "r", encoding="utf-8") as file:
        json_data = json.load(file)


def predict_excess(tick: int) -> float:  # returns extra energy
    wind_power = predict_wind_power()

    wind_energy = []
    solar_energy = []
    robo_solar_energy = []

    consumer_energy = sum([predict_consumer(obj, tick) for obj in psm.objects])


def predict_wind_power() -> List[float]:
    if psm.tick >= 1:
        base_0 = psm.wind.then[0]
        base_1 = psm.wind.then[1]
        wind_power_prediction = [base_0 + (base_1 - base_0) * wind_tick for wind_tick in range(101)]
    else:
        wind_power_prediction = psm.forecasts.wind.lows
        print(len(wind_power_prediction))

    for wind_generator in psm.objects:
        if wind_generator.type != "wind":
            continue

        wind_coefficient = mean(
            [
                wind_energy / (wind_power_prediction[index] ** 3)
                for index, wind_energy in enumerate(wind_generator.power.then + [wind_generator.power.now])  # TODO
            ]
        )

    return wind_power_prediction


def predict_consumer(consumer, tick: int) -> float:
    if consumer.type == "houseA":
        prediction = psm.forecasts.houseA[tick] + 0.5
    elif consumer.type == "houseB":
        prediction = psm.forecasts.houseB[tick] + 0.5
    elif consumer.type == "factory":
        prediction = psm.forecasts.factory[tick] + 0.5
    elif consumer.type == "hospital":
        prediction = psm.forecasts.hospital[tick] + 0.25
    else:
        prediction = 0

    return prediction


predict_excess(12)
