import matplotlib.pyplot as plt
import csv
from pathlib import Path


def mean(iterable):
    return sum(iterable) / len(iterable)


csv_path = Path("forecasts/forecast_test_4.csv")
ticks = range(1, 101)

with open(csv_path, "r") as csv_file:
    wind1, wind2, wind3, wind4, wind5, wind_left, wind_right, sun, hospital, factory, houseA, houseB = map(
        lambda tup: list(map(lambda val: float(val), tup)),
        map(lambda tup: tup[1:], zip(*list(csv.reader(csv_file))))
    )

plt.plot(ticks, (0,) * 100)
plt.plot(ticks, (20,) * 100)

plt.plot(
    ticks,
    list(map(
        lambda a, b, c, d, e: (a + b + c + d + e) / 5,
        wind1, wind2, wind3, wind4, wind5
    )),
    label="tables"
)
plt.plot(
    ticks,
    list(map(
        lambda a, b: (a + b) / 2,
        wind_left, wind_right
    )),
    label="center"
)

plt.legend()
plt.show()
