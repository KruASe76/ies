import ips
from dataclasses import dataclass
from typing import List
from math import exp
import json

psm = ips.init()
# psm = ips.from_log("logs/logs_2_evening.json", 40)


@dataclass
class MarketOffer:
    start_tick: int
    end_tick: int
    amount: float  # купить - знак "+", продать - знак "-"
    price: float
    check: bool = True


def op(tick: int, action: int) -> float:  # action > 0 -> buy, action < 0 -> sell
    tick = tick % 48

    if 0 <= tick <= 11:
        return 2.5 if action > 0 else 2.8
    elif 12 <= tick <= 23:
        return 4 if action > 0 else 4.8
    elif 24 <= tick <= 35:
        return 5.5 if action > 0 else 5.8
    else:
        return 8 if action > 0 else 9


MARKET_OFFERS: List[MarketOffer] = [
    # закупка старт
    MarketOffer(0, 11, 5, op(psm.tick, +1), False),

    # продажа день 1
    MarketOffer(11, 40, -10, op(psm.tick, -1), False),

    # продажа дорого 1
    # MarketOffer(34, 46, -7, op(psm.tick, -1), False),

    # покупка ночь середина
    # MarketOffer(40, 53, 5, op(psm.tick, +1), False),
    MarketOffer(53, 59, 8, op(psm.tick, +1), False),

    # продажа день 2
    MarketOffer(61, 88, -10, op(psm.tick, -1), False),

    # продажа дорого 2
    # MarketOffer(82, 94, -7, op(psm.tick, -1), False),

    # покупка финал
    MarketOffer(89, 98, 5, op(psm.tick, +1), False),
    # MarketOffer(95, 98, 15, op(psm.tick, +1), False),

    # стабильная продажа
    # MarketOffer(0, 100, -5, op(psm.tick, -1), False),
    # MarketOffer(0, 100, -5, op(psm.tick, -1), False),
    # MarketOffer(0, 100, -5, op(psm.tick, -1), False),
    # стабильная покупка
    # MarketOffer(0, 100, 5, op(psm.tick, +1), False),
    # MarketOffer(0, 100, 5, op(psm.tick, +1), False),
    # MarketOffer(0, 100, 5, op(psm.tick, +1), False),
]


@dataclass
class StorageTransaction:
    start_tick: int
    end_tick: int
    amount: float  # зарядить - знак "+", разрядить - знак "-"
    check: bool = True


STORAGE_TRANSACTIONS: List[StorageTransaction] = [
    # зарядка день 1
    # StorageTransaction(19, 32, 10, False),

    # разрядка ночь середина
    # StorageTransaction(42, 53, -10, False),

    # зарядка день 2
    # StorageTransaction(69, 82, 10, False),

    # разрядка финал
    # StorageTransaction(89, 100, -10, False),

    # стабильная зарядка
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False),
    # стабильная зарядка
    # StorageTransaction(0, 100, +5, False),
    # StorageTransaction(0, 100, +5, False),
    # StorageTransaction(0, 100, +5, False),
]


solar_config = {
    "s6": ("west", (1.46, -3), (1.46, 0)),
    "sB": ("west", (1.46, -3), (1.46, 0)),
    "r7": ("west", (2.28, -5.22), (2.28, 0.4)),
}

day_1_start = -1 + 6
day_1_end = -1 + 49
day_2_start = -1 + 54
day_2_end = -1 + 97


FILENAME = "chekanshchiki_temp.json"

if psm.tick == 0:
    json_data = {
        "market": [0] * 110,
        "storage": [None] * 110
    }
else:
    with open(FILENAME, "r", encoding="utf-8") as file:
        json_data = json.load(file)


storages = tuple(filter(lambda obj: obj.type == "storage", psm.objects))
robo_solars = tuple(filter(lambda obj: obj.type == "solarRobot", psm.objects))


power_delta = (
        psm.total_power.generated - psm.total_power.consumed - psm.total_power.losses + json_data["market"][psm.tick]
)
# json_data["power_delta"].append(power_delta)
print(f"POWER DELTA: {power_delta}")


def storage_power(temperature: float) -> float:
    def helper(temperature: float) -> float:
        return 0.8 / (1 + exp(0.1 * (40 - temperature)))

    coefficient = 1 + helper(20) - helper(temperature)

    return 10 * coefficient


for offer in MARKET_OFFERS:
    if offer.start_tick <= psm.tick < offer.end_tick:
        if offer.amount < 0 and (power_delta > 0 if offer.check else True):
            psm.orders.sell(-offer.amount, offer.price)

            json_data["market"][psm.tick + 2] -= -offer.amount
            print(f"sold {-offer.amount} for {offer.price} each")

        elif offer.amount > 0 and (power_delta < 0 if offer.check else True):
            psm.orders.buy(offer.amount, offer.price)

            json_data["market"][psm.tick + 2] += offer.amount
            print(f"bought {offer.amount} for {offer.price} each")

for transaction in STORAGE_TRANSACTIONS:
    if not transaction.start_tick <= psm.tick < transaction.end_tick:
        continue

    if transaction.amount < 0:
        not_low_charge_storages = tuple(
            filter(
                lambda storage: storage.charge.now > 5,
                storages
            )
        )

        if not_low_charge_storages:
            selected_storage = max(not_low_charge_storages, key=lambda storage: storage_power(storage.temp.now))
        else:
            selected_storage = max(storages, key=lambda storage: storage_power(storage.temp.now))
    else:
        not_full_storages = tuple(
            filter(
                lambda storage: storage.charge.now < 55,
                storages
            )
        )

        if not not_full_storages:
            continue

        selected_storage = max(not_full_storages, key=lambda storage: storage_power(storage.temp.now))

    if transaction.amount > 0 and (power_delta > 0 if transaction.check else True):
        energy = min(transaction.amount, storage_power(selected_storage.temp.now), 60 - selected_storage.charge.now)

        psm.orders.charge(selected_storage.address[0], energy)
        print(f"charged {selected_storage.address[0]} by {energy}")

    elif transaction.amount < 0 and (power_delta < 0 if transaction.check else True):
        energy = min(-transaction.amount, storage_power(selected_storage.temp.now), selected_storage.charge.now)

        psm.orders.discharge(selected_storage.address[0], energy)
        print(f"DIScharged {selected_storage.address[0]} by {energy}")


# rotating suns
for robo_solar, config in solar_config.items():
    if not robo_solar.startswith("r"):
        continue

    if config[0] == "east":
        robo_start_angle = 49 - 10
        robo_end_angle = 49 + 20
    else:
        robo_start_angle = 49 + 20
        robo_end_angle = 49 - 10

    if psm.tick not in range(day_1_start, day_1_end + 1) and psm.tick not in range(day_2_start, day_2_end + 1):
        psm.orders.robot(robo_solar, robo_start_angle)
    elif psm.tick in range(day_1_start, day_1_end + 1):
        psm.orders.robot(
            robo_solar,
            robo_start_angle +
            (robo_end_angle - robo_start_angle) *
            (psm.tick - day_1_start) / (day_1_end - day_1_start)
        )
    elif psm.tick in range(day_2_start, day_2_end + 1):
        psm.orders.robot(
            robo_solar,
            robo_start_angle +
            (robo_end_angle - robo_start_angle) *
            (psm.tick - day_2_start) / (day_2_end - day_2_start)
        )


with open(FILENAME, "w", encoding="utf-8") as file:
    json.dump(json_data, file, indent=4)


psm.save_and_exit()
# print(f"{psm.tick}:", psm.orders.get())
