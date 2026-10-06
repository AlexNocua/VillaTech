from decimal import Decimal as D

def calculate(data):
    material = data['grams'] * data['spool_price'] / data['spool_grams']
    depreciation = data['hours'] * data['printer_price'] / data['useful_hours']
    maintenance = data['hours'] * data['maintenance_hour']
    energy = data['hours'] * data['watts'] / D(1000) * data['kwh_price']
    production = material + depreciation + maintenance + energy
    reserve = production * data['waste'] / D(100)
    cost = production + reserve + data['labor'] + data['extras']
    price = cost / (D(1) - data['margin'] / D(100))
    return {key:value.quantize(D('.01')) for key,value in dict(material=material,depreciation=depreciation,maintenance=maintenance,energy=energy,reserve=reserve,cost=cost,price=price).items()}
