import peewee

from src.config import config
from src.models.pigeon import ExplorationPlanet, ExplorationPlanetLocation, ExplorationAction, ExplorationActionScenario


def process_items():
    pass


def process_scenarios():
    import yaml
    if not isinstance(config.settings.base_database, peewee.SqliteDatabase):
        raise Exception('No, I don\'t think so.')

    ExplorationActionScenario.drop_table()
    ExplorationActionScenario.create_table()
    # for table in [ExplorationPlanet, ExplorationPlanetLocation, ExplorationAction, ExplorationActionScenario]:
    #     table.drop_table()
    #     table.create_table()

    with open('resources/scenarios/scenarios.yml', 'r', encoding='utf8') as file:
        scenarios = yaml.safe_load(file)
        for raw_planet in scenarios['planets']:
            planet = ExplorationPlanet.get_or_none(name=raw_planet['name']) or ExplorationPlanet()
            planet.image_url = raw_planet['image_url']
            planet.name = raw_planet['name']
            planet.save()
            for raw_location in raw_planet['locations']:
                location = ExplorationPlanetLocation.get_or_none(name=raw_location['name'],
                                                                 planet=planet) or ExplorationPlanetLocation()
                location.image_url = raw_location.get('image_url')
                location.name = raw_location['name']
                location.planet = planet
                location.save()
                for raw_action in raw_location['actions']:
                    action = ExplorationAction.get_or_none(name=raw_action['name'],
                                                           location=location) or ExplorationAction()
                    action.name = raw_action['name']
                    action.symbol = raw_action['emoji']
                    action.location = location
                    action.planet = planet
                    action.save()
                    for raw_scenario in raw_action['scenarios']:
                        stats = [0 if x == '' else int(x) for x in raw_scenario['stats'].split(',')]
                        scenario = ExplorationActionScenario()
                        scenario.action = action
                        scenario.text = raw_scenario['text']
                        scenario.gold = stats[0]
                        scenario.health = stats[1]
                        scenario.happiness = stats[2]
                        scenario.cleanliness = stats[3]
                        scenario.food = stats[4]
                        scenario.experience = sum([abs(x) for x in stats])
                        scenario.save()
