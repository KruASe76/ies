import ips
from dataclasses import dataclass
from typing import List
import json
import os


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


psm = ips.init()


WEAR_LIMIT = 0.45

MARKET: List[MarketOffer] = [
    # закупка старт
    MarketOffer(1, 15, 5, 3, False),
    # продажа день 1
    MarketOffer(20, 40, -12, 6, ),
    MarketOffer(25, 35, -10, 6, ),
    # покупка ночь середина
    MarketOffer(45, 65, 10, 3, ),
    # продажа день 2
    MarketOffer(70, 90, -12, 6, ),
    MarketOffer(76, 84, -12, 6, ),
    # продажа финал
    # MarketOffer(89, 100, -21, 5, False),
    # стабильная продажа
    # MarketOffer(0, 100, -5, 4, False),
    # MarketOffer(0, 100, -5, 4, False),
    # MarketOffer(0, 100, -5, 4, False)
]

BATTERY: List[StorageTransaction] = [
    # # зарядка день 1
    # StorageTransaction(21, 41, 15, ),
    # # разрядка ночь середина 1
    # StorageTransaction(43, 58, -15, False),
    # # разрядка ночь середина 2
    # StorageTransaction(58, 68, -5, False),
    # # зарядка день 2
    # StorageTransaction(70, 85, 15, ),
    # # разрядка на продажу финал
    # StorageTransaction(90, 100, -27, False),
    # # стабильная зарядка
    # # StorageTransaction(0, 100, -5, False),
    # # StorageTransaction(0, 100, -5, False),
    # # StorageTransaction(0, 100, -5, False)
]


if psm.tick == 1:
    if "chetverochka_temp.json" in os.walk(".."):
        os.remove("chetverochka_temp.json")
    json_data = {"power_delta": [], "line_off": [], "market": dict.fromkeys(map(str, range(110)), 0)}
else:
    with open("chetverochka_temp.json", "r", encoding="utf-8") as file:
        json_data = json.load(file)


storages = list(filter(lambda obj: obj.type == "storage", psm.objects))


line_to_off = None
if json_data["line_off"]:
    line_to_off = json_data["line_off"]
    json_data["line_off"] = []


for station in filter(lambda obj: obj.type in ("main", "miniA", "miniB"), psm.objects):
    for line_number in range(1, 3 if station.type == "miniB" else 4):
        line = ips.Line(id=station.id, line=line_number)
        try:
            network = tuple(filter(
                lambda pl: pl.location and pl.location[-1] == line,
                psm.networks.values()
            ))[0]
        except IndexError:
            print(f"{station.address[0]} {line_number} not connected")
            continue

        psm.orders.line_on(station.address[0], line_number)
        print(f"{station.address[0]} {line_number}")

        if not json_data["line_off"] and network.wear >= WEAR_LIMIT:
            json_data["line_off"] = [station.address[0], line_number]
            print(f"planned off: {station.address[0]} {line_number}")
            is_off_planned = True


if line_to_off:  # ..._left turned on
    psm.orders.line_off(*line_to_off)
    print(f"line off: {' '.join(map(str, line_to_off))}")

    generators_left = tuple(filter(lambda obj: obj.type in ("solar", "wind") and line not in obj.path[0], psm.objects))
    power_income_left = sum(map(lambda gen: gen.power.now.generated, generators_left))

    storages_left = list(filter(lambda storage: line not in storage.path[0], storages))
    wanted = (max(
        psm.total_power.consumed - power_income_left + json_data["market"][str(psm.tick + 1)] + 1, 0
    ) / len(storages_left)) if storages_left else 0
    print(f"discharging {wanted} from {len(storages_left)} storages")
    for storage in storages_left:
        psm.orders.discharge(storage.address[0], min(min(wanted, 15), storage.charge.now))


power_delta = psm.total_power.generated - psm.total_power.consumed - psm.total_power.losses
json_data["power_delta"].append(power_delta)
print(f"POWER DELTA: {power_delta}")


for offer in MARKET:
    if offer.start_tick <= psm.tick < offer.end_tick:
        if offer.amount < 0 and (power_delta > 0 if offer.check else True):
            psm.orders.sell(-offer.amount, offer.price)
            json_data["market"][str(psm.tick + 2)] -= -offer.amount
            print(f"sold {-offer.amount} for {offer.price} each")
        elif offer.amount > 0 and (power_delta < 0 if offer.check else True):
            psm.orders.buy(offer.amount, offer.price)
            json_data["market"][str(psm.tick + 2)] += offer.amount
            print(f"bought {offer.amount} for {offer.price} each")

for transaction in BATTERY:
    if transaction.start_tick <= psm.tick < transaction.end_tick:
        storages_left = list(filter(lambda storage: line not in storage.path[0], storages))
        for storage in storages_left:
            if transaction.amount > 0 and (power_delta > 0 if transaction.check else True):
                each = min(min(transaction.amount / len(storages_left), 15), 100 - storage.charge.now)
                psm.orders.charge(storage.address[0], each)
                print(f"charged {storage.address[0]} by {each}")
            elif transaction.amount < 0 and (power_delta < 0 if transaction.check else True):
                each = min(min(-transaction.amount / len(storages_left), 15), storage.charge.now)
                psm.orders.discharge(storage.address[0], each)
                print(f"discharged {storage.address[0]} by {each}")


psm.orders.add_graph(0, psm.forecasts.sun)
for index, solar in enumerate(filter(lambda obj: obj.type == "solar", psm.objects), start=1):
    psm.orders.add_graph(index, list(map(lambda line: line.generated, solar.power.then + [solar.power.now])))


with open("chetverochka_temp.json", "w", encoding="utf-8") as file:
    json.dump(json_data, file, indent=4)


if psm.tick == 100:
    os.remove("chetverochka_temp.json")


print()
for storage in storages:
    print(f"{storage.address[0]}: {storage.charge.now}")

print()
print(f"Генерация: {psm.total_power.generated}")
print(f"Потребление: {psm.total_power.consumed}")
print(f"Потери: {psm.total_power.losses}")
print(f"Биржа: {psm.total_power.external}")

try:
    psm.save_and_exit()
except:
    pass
