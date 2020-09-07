from openweathermap.api.api import OpenWeatherApi










if __name__ == "__main__":

    api = OpenWeatherApi("ab9a9e95335043c2afb67f9a576c38b4")

    city = api.by_q("Munstergeleen")

    print(city.temperature_info.temperature)



"""

{
    'base': 'stations',
    'visibility': 6000,
    'dt': 1580425739,
    'timezone': 3600,
    'id': 2751283,
    'name': 'Munstergeleen',
    'cod': 200

    'wind':
    {
        'speed': 20.8,
        'deg': 230
    },
    
    'rain':
    {
        '1h': 1.02
    },
    
    'clouds':
    {
        'all': 75
    },
    
    'sys': 
    {
        'type': 1,
        'id': 1525,
        'country': 'NL',
        'sunrise': 1580454939,
        'sunset': 1580487841
    },
    

}
"""
