import csv
from dataclasses import dataclass
from pathlib import Path
from pprint import pprint

import matplotlib.pyplot as plt
from typing import List

import ips


@dataclass
class Forecast:
    wind_from: List[float]
    wind_to: List[float]
    sun_east: List[float]
    sun_west: List[float]
    hospital: List[float]
    factory: List[float]
    houseA: List[float]
    houseB: List[float]


forecast_path = Path("forecasts/forecast_3_auto_1_and_2.csv")
logs_path = Path("logs/logs_4_meme.json")
ticks = range(100)


with open(forecast_path, "r") as csv_file:
    forecast = Forecast(
        *map(
            lambda tup: list(map(lambda val: float(val), tup[1:])),
            zip(*tuple(csv.reader(csv_file)))
        )
    )


psm = ips.from_log(logs_path, 100)


def prints():
    pprint(psm.objects)
    pprint(psm.networks)
    print(psm.total_power.generated, psm.total_power.consumed, psm.total_power.losses)
    print(*map(
        lambda solar: sum(list(map(lambda line: line.generated, solar.power.then[1:])) + [solar.power.now.generated]),
        filter(lambda obj: obj.type in ("solar", "solarRobot"), psm.objects)
    ))


def generators():
    solars = filter(lambda obj: obj.type in ("solar", "solarRobot"), psm.objects)
    for solar in solars:
        plt.plot(
            ticks,
            list(map(lambda line: line.generated, solar.power.then[1:])) + [solar.power.now.generated], label=solar.address[0]
        )

    # winds = filter(lambda obj: obj.type == "wind", psm.objects)
    # for wind in winds:
    #     plt.plot(
    #         ticks,
    #         list(map(lambda line: line.generated, wind.power.then[1:])) + [wind.power.now.generated], label=wind.address[0]
    #     )

    # plt.plot(ticks, wind3, label="wind3")
    plt.plot(ticks, forecast.sun_east, label="sun")
    plt.plot(ticks, forecast.sun_west, label="sun")

    plt.legend()
    plt.show()


def consumers():
    all = filter(lambda obj: obj.type in ("hospital", "factory", "houseA", "houseB"), psm.objects)

    for obj in all:
        plt.plot(
            ticks,
            list(map(lambda line: line.consumed, obj.power.then[1:])) + [obj.power.now.consumed], label=" ".join(obj.address)
        )

    plt.legend()
    plt.show()


def consumer_sum():
    houseA_prices = tuple(map(float, input("Цены домов A: ").split()))
    houseB_prices = tuple(map(float, input("Цены домов B: ").split()))
    hospital_count = int(input("Больницы: "))
    factory_count = int(input("Заводы: "))

    plt.plot(ticks, (0,) * 100)
    plt.plot(ticks, (40,) * 100)

    plt.plot(
        ticks,
        list(map(
            lambda hospitals, factories, *houses: hospitals * hospital_count + factories * factory_count + sum(houses),
            forecast.hospital, forecast.factory,
            *(map(lambda forecast: forecast + 0.82 * (5 - price) ** 2.6, forecast.houseA) for price in houseA_prices),
            *(map(lambda forecast: forecast + 0.24 * (9 - price) ** 2.2, forecast.houseB) for price in houseB_prices)
        ))
    )

    plt.show()


def test_on():
    is_off = False
    for station in filter(lambda obj: obj.type in ("main", "miniA", "miniB"), psm.objects):
        for line_number in range(1, 3 if station.type == "miniB" else 4):
            try:
                network = tuple(filter(
                    lambda pl: pl.location and pl.location[-1].id == station.id and pl.location[-1].line == line_number,
                    psm.networks.values()
                ))[0]
            except IndexError:
                print(station.address[0], line_number, "не подключена")
                continue

            psm.orders.line_on(station.address[0], line_number)
            print(station.address[0], line_number)

            if not is_off and network.wear >= 0.3:
                psm.orders.line_off(station.address[0], line_number)
                is_off = True


def coefficients():
    for forecast_path, logs_path, index in zip(
            (Path("forecasts/forecast_prod_1.csv"),),
            (Path("logs/logs_prod_1.json"),),
        range(1, 2)
    ):
        with open(forecast_path, "r") as csv_file:
            # noinspection PyUnusedLocal
            wind1, wind2, wind3, wind4, wind5, wind_left, wind_right, sun, hospital, factory, houseA, houseB = map(
                lambda tup: list(map(lambda val: float(val), tup)),
                map(lambda tup: tup[1:], zip(*list(csv.reader(csv_file))))
            )
        psm = ips.from_log(logs_path, 100)

        solars = filter(lambda obj: obj.type in ("solar", "solarRobot"), psm.objects)
        for solar in solars:
            plt.plot(
                ticks,
                list(map(
                    lambda line, index: line.generated / max(psm.forecasts.sun[index], 0.1),
                    solar.power.then[1:] + [solar.power.now], range(100)
                )),
                label=f"{solar.address[0]} {index}"
            )

        winds = filter(lambda obj: obj.type == "wind", psm.objects)
        for wind, forecast in zip(winds, "ДЖД"):
            print(wind.address[0], forecast)
            plt.plot(
                ticks,
                list(map(
                    lambda line, index: line.generated / psm.forecasts.wind[forecast][index],
                    wind.power.then[1:] + [wind.power.now], range(100)
                )),
                label=f"{wind.address[0]} {index}"
            )

    plt.legend()
    plt.show()


# prints()
generators()
consumers()
# consumer_sum()
# test_on()
# coefficients()

# psm = ips.from_log(logs_path, 87)
#
# for index, net in psm.networks.items():
#     print("== Энергорайон", index, "==")
#     print("Адрес:", net.location)          # [ (ID подстанции, № линии) ]
#     print("Включен:", net.online) # bool
#     print("Генерация:", net.upflow) # float
#     print("Потребление:", net.downflow) # float
#     print("Потери:", net.losses) # float
#
# print()
#
#
# for tick in range(19, 23):
#     print(f"=== TICK {tick} ===")
#     psm = ips.from_log(logs_path, tick)
#
#     for receipt in psm.exchange:
#         print("Контрагент:", receipt.source)    # "exchange" = оператор,    #     иначе  = другой игрок
#         print("Объём:", receipt.flux)    # Плюс = покупка, минус = продажа
#         print("Цена за МВт:", receipt.price)
#         print("----------")



# print(psm.wind.then, psm.wind.now)
#
# print()
#
# for obj in psm.objects:
#     if obj.type == "wind":
#         print([energy.generated for energy in obj.power.then], obj.power.now.generated)


for obj in psm.objects:
    if obj.type == "storage":
        print(f"=== {obj.address[0]} ===")
        print(*tuple(enumerate(obj.power.then)), sep="\n")
        print(("now", obj.power.now))
        print()
