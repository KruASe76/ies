import ips
from dataclasses import dataclass
from typing import List
from itertools import chain
from math import e


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
        return 2.5 if action > 0 else 2.5
    elif 12 <= tick <= 23:
        return 4 if action > 0 else 5
    elif 24 <= tick <= 35:
        return 5.5 if action > 0 else 6.5
    else:
        return 8 if action > 0 else 10.5


MARKET_OFFERS: List[MarketOffer] = [
    # закупка старт
    MarketOffer(0, 12, 15, optimal_price(psm.tick, +1), False),
    # продажа день 1
    MarketOffer(24, 36, -10, optimal_price(psm.tick, -1), ),
    # покупка ночь середина
    MarketOffer(43, 48, 5, optimal_price(psm.tick, +1), ),
    MarketOffer(48, 60, 5, optimal_price(psm.tick, +1), ),
    # продажа день 2
    MarketOffer(72, 84, -8, optimal_price(psm.tick, -1), ),
    # продажа финал
    MarketOffer(85, 95, -5, optimal_price(psm.tick, -1), False),
    # стабильная продажа
    # MarketOffer(0, 100, -5, psm.tick, False),
    # MarketOffer(0, 100, -5, psm.tick, False),
    # MarketOffer(0, 100, -5, psm.tick, False)
]

STORAGE_TRANSACTIONS: List[StorageTransaction] = [
    # зарядка день 1
    StorageTransaction(21, 41, 10, ),
    # разрядка ночь середина 1
    StorageTransaction(43, 58, -10, False),
    # разрядка ночь середина 2
    StorageTransaction(58, 68, -5, False),
    # зарядка день 2
    StorageTransaction(70, 85, 10, ),
    # разрядка на продажу финал
    StorageTransaction(85, 95, -10, False),
    # стабильная зарядка
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False),
    # StorageTransaction(0, 100, -5, False)
]


robo_start_angle = 50 - 22
robo_end_angle = 50 + 35
day_1_start = 6
day_1_end = 49
day_2_start = 54
day_2_end = 97


storages = tuple(filter(lambda obj: obj.type == "storage", psm.objects))
robo_solars = tuple(filter(lambda obj: obj.type == "solarRobot", psm.objects))

# storage_actions = {storage.address[0]: 0 for storage in storages}


power_delta = psm.total_power.generated - psm.total_power.consumed - psm.total_power.losses
# json_data["power_delta"].append(power_delta)
print(f"POWER DELTA: {power_delta}")


def storage_current_power(temperature: float) -> float:
    def helper(temperature: float) -> float:
        return 0.8 / (1 + e ** (0.1 * (40 - temperature)))

    return 1 + helper(20) - helper(temperature)


for offer in MARKET_OFFERS:
    if offer.start_tick <= psm.tick < offer.end_tick:
        if offer.amount < 0 and (power_delta > 0 if offer.check else True):
            psm.orders.sell(-offer.amount, offer.price)

            # json_data["market"][str(psm.tick + 2)] -= -offer.amount
            print(f"sold {-offer.amount} for {offer.price} each")

        elif offer.amount > 0 and (power_delta < 0 if offer.check else True):
            psm.orders.buy(offer.amount, offer.price)

            # json_data["market"][str(psm.tick + 2)] += offer.amount
            print(f"bought {offer.amount} for {offer.price} each")


for transaction in STORAGE_TRANSACTIONS:
    if not transaction.start_tick <= psm.tick < transaction.end_tick:
        continue

    capable_storages = tuple(
        filter(
            lambda storage: storage_current_power(storage) <= storage.charge.now if transaction.check else True,
            storages
        )
    )
    selected_storage = max(capable_storages, key=lambda storage: storage_current_power(storage))

    if transaction.amount > 0 and (power_delta > 0 if transaction.check else True):
        energy = min(transaction.amount, storage_current_power(selected_storage), 60 - selected_storage.charge.now)

        psm.orders.charge(selected_storage.address[0], energy)
        print(f"charged {selected_storage.address[0]} by {energy}")

    elif transaction.amount < 0 and (power_delta < 0 if transaction.check else True):
        energy = min(-transaction.amount, storage_current_power(selected_storage), selected_storage.charge.now)

        psm.orders.discharge(selected_storage.address[0], energy)
        print(f"discharged {selected_storage.address[0]} by {energy}")


# rotating suns
if psm.tick not in tuple(chain(range(day_1_start, day_1_end + 1), range(day_2_start, day_2_end + 1))):
    for robo_solar in robo_solars:
        psm.orders.robot(robo_solar.address[0], robo_start_angle)
elif psm.tick in range(day_1_start, day_1_end + 1):
    for robo_solar in robo_solars:
        psm.orders.robot(
            robo_solar.address[0],
            robo_start_angle + \
                (robo_end_angle - robo_start_angle) / (day_1_end - day_1_start) * \
                (psm.tick - day_1_start)
        )
elif psm.tick in range(day_2_start, day_2_end + 1):
    for robo_solar in robo_solars:
        psm.orders.robot(
            robo_solar.address[0],
            robo_start_angle + \
            (robo_end_angle - robo_start_angle) / (day_2_end - day_2_start) * \
            (psm.tick - day_2_start)
        )


psm.save_and_exit()
