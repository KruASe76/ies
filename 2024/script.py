import ips
from dataclasses import dataclass
from typing import List
from math import pow, exp
import json

psm = ips.init()


@dataclass
class MarketOffer:
    start_tick: int
    end_tick: int
    amount: float  # купить - знак "+", продать - знак "-"
    price: float
    check: bool = True


@dataclass
class StorageTransaction:
    start_tick: int
    end_tick: int
    amount: float  # зарядить - знак "+", разрядить - знак "-"
    check: bool = True


def optimal_price(tick: int, action: int) -> float:  # action > 0 -> buy, action < 0 -> sell
    tick = tick % 48

    if 0 <= tick <= 11:
        return 2.5 if action > 0 else 2.4
    elif 12 <= tick <= 23:
        return 4 if action > 0 else 4.4
    elif 24 <= tick <= 35:
        return 5.5 if action > 0 else 5.4
    else:
        return 8 if action > 0 else 7.4


MARKET_OFFERS: List[MarketOffer] = [
    # закупка старт
    MarketOffer(0, 12, 15, optimal_price(psm.tick, +1), False),
    # продажа день 1
    MarketOffer(24, 36, -30, optimal_price(psm.tick, -1), ),
    # покупка ночь середина
    MarketOffer(43, 48, 5, optimal_price(psm.tick, +1), ),
    MarketOffer(48, 60, 5, optimal_price(psm.tick, +1), ),
    # продажа день 2
    MarketOffer(72, 84, -30, optimal_price(psm.tick, -1), ),
    # продажа финал
    # MarketOffer(85, 95, -5, optimal_price(psm.tick, -1), False),
    # покупка финал
    MarketOffer(88, 98, 8, optimal_price(psm.tick, +1), )
    # стабильная продажа
    # MarketOffer(0, 100, -5, optimal_price(psm.tick, -1), False),
    # MarketOffer(0, 100, -5, optimal_price(psm.tick, -1), False),
    # MarketOffer(0, 100, -5, optimal_price(psm.tick, -1), False),
    # стабильная покупка
    # MarketOffer(0, 100, 5, optimal_price(psm.tick, +1), False),
    # MarketOffer(0, 100, 5, optimal_price(psm.tick, +1), False),
    # MarketOffer(0, 100, 5, optimal_price(psm.tick, +1), False),
]

STORAGE_TRANSACTIONS: List[StorageTransaction] = [
    # зарядка день 1
    StorageTransaction(19, 34, 10, ),
    # разрядка ночь середина 1
    StorageTransaction(44, 52, -10, False),
    StorageTransaction(51, 68, -10, False),
    # зарядка день 2
    StorageTransaction(69, 84, 10, ),
    # разрядка финал
    StorageTransaction(88, 100, -10, False),
    # стабильная зарядка
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False),
    # стабильная зарядка
    # StorageTransaction(0, 100, +5, False),
    # StorageTransaction(0, 100, +5, False),
    # StorageTransaction(0, 100, +5, False),
]

FILENAME = "chekanshchiki_temp.json"

if psm.tick == 0:
    json_data = {"market": [0] * 101}
else:
    with open(FILENAME, "r", encoding="utf-8") as file:
        json_data = json.load(file)

robo_start_angle = 49 - 43
robo_end_angle = 49 + 39
day_1_start = -1 + 6
day_1_end = -1 + 49
day_2_start = -1 + 54
day_2_end = -1 + 97

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
        low_charge_storages = tuple(
            filter(
                lambda storage: storage.charge.now < 15,
                storages
            )
        )

        if low_charge_storages:
            selected_storage = min(low_charge_storages, key=lambda storage: storage.charge.now)
        else:
            selected_storage = max(storages, key=lambda storage: storage_power(storage.temp.now))
    else:
        selected_storage = max(storages, key=lambda storage: storage_power(storage.temp.now))


    if transaction.amount > 0 and (power_delta > 0 if transaction.check else True):
        energy = min(transaction.amount, storage_power(selected_storage.temp.now), 60 - selected_storage.charge.now)

        psm.orders.charge(selected_storage.address[0], energy)
        print(f"charged {selected_storage.address[0]} by {energy}")

    elif transaction.amount < 0 and (power_delta < 0 if transaction.check else True):
        energy = min(-transaction.amount, storage_power(selected_storage.temp.now), selected_storage.charge.now)

        psm.orders.discharge(selected_storage.address[0], energy)
        print(f"DIScharged {selected_storage.address[0]} by {energy}")


def ease_in_cubic(x: float) -> float:
    return pow(x, 3)

def ease_out_cubic(x: float) -> float:
    return 1 - pow(1 - x, 3)


# rotating suns
robo_solar = "r2"
if psm.tick in range(day_1_start):
    psm.orders.robot(robo_solar, 4)
elif psm.tick in range(day_1_start, day_1_end + 1):
    psm.orders.robot(
        robo_solar,
        4 +
        90 / (day_1_end - day_1_start) *
        (psm.tick - day_1_start)
    )
elif psm.tick > day_1_end:
    psm.orders.robot(robo_solar, 49)

robo_solar = "r5"
if psm.tick in range(day_1_start):
    psm.orders.robot(robo_solar, robo_start_angle)
elif psm.tick in range(day_1_start, day_1_end + 1):
    psm.orders.robot(
        robo_solar,
        robo_start_angle +
        (robo_end_angle - robo_start_angle) *
        (psm.tick - day_1_start) / (day_1_end - day_1_start)
        # ease_in_cubic((psm.tick - day_1_start) / (day_1_end - day_1_start))
    )
elif psm.tick > day_1_end:
    psm.orders.robot(robo_solar, robo_end_angle)


psm.save_and_exit()
