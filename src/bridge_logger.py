import datetime
import time

import peewee
from wrappers.hue_bridge import GetLightsCall, GetLightCall, HueBridgeCall, HueBridgeCache, AuthenticateCall, Light

class SqliteBaseModel(peewee.Model):
    class Meta:
        legacy_table_names = False
        only_save_dirty = True
        database = peewee.SqliteDatabase("data/data.sqlite")

class LightStateLog(SqliteBaseModel):
    created_at = peewee.DateTimeField (null = False, default = lambda : datetime.datetime.utcnow())
    on         = peewee.BooleanField  (null = False)
    light_id   = peewee.IntegerField  (null = False)
    brightness = peewee.IntegerField  (null = False)

database = SqliteBaseModel._meta.database

with database.connection_context():
    # database.drop_tables([LightStateLog])
    database.create_tables([LightStateLog])


class LightStateLogger:
    __slots__ = ()

    @classmethod
    def log(self, light: Light):
        LightStateLog.create(
            on = light.state.on,
            light_id = light.id,
            brightness = light.state.brightness
        )

HueBridgeCall.set_ip("192.168.178.172")

username = HueBridgeCache.get_username()
if username is None:
    call = AuthenticateCall("Clark API Client")
    username = call.call()
    HueBridgeCache.set_username(username)

def get_light_id(name: str) -> int:
    call = GetLightsCall(username)
    for light in call.call():
        if light.name == name:
            return light.id

id = get_light_id("Clark")
call = GetLightCall(username, id)

def log():
    pass

def log_loop():
    last_state = HueBridgeCache.get_last_known_state()
    failures = 0
    while True:
        try:
            light = call.call()
        except:
            failures += 1
            sleep_time = failures * 5
            print(f"Call failed for the {failures}th time... Trying again in {sleep_time } seconds")
            time.sleep(sleep_time)
            continue
        if last_state is None or last_state["on"] != light.state.on:
            print(last_state["on"], light.state.on)
            LightStateLogger.log(light)
            HueBridgeCache.set_last_known_state(light.state)
            last_state = HueBridgeCache.get_last_known_state()
        time.sleep(60)

if __name__ == "__main__":
    print("Started logging...")
    try:
        log_loop()
    except Exception as e:
        print(datetime.datetime.utcnow(), e)
    print("Stopped logging...")
