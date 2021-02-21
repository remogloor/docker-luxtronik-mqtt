import sys, os, requests, datetime, re, logging, logging.handlers
import paho.mqtt.publish as publish
import pytz
import time
import argparse
import asyncio
import websockets
import xml.etree.ElementTree as ET
import configparser
from time import sleep

# Sleep time.
LOOP_SLEEP = 10
# Debug mode.
DEBUG = 0


class WpMqtt():
    def init(self, logger):
        self.luxtronik_hostname = os.environ.get('luxtronik_hostname','')
        self.luxtronik_port = os.environ.get('luxtronik_port','')
        self.luxtronik_login = "LOGIN;" + os.environ.get('luxtronik_pin','')
        self.luxtronik_url = "ws://" + self.luxtronik_hostname + ":" + self.luxtronik_port
        
        self.mqtt_client_id = os.environ.get('mqtt_client_id','')
        self.mqtt_host = os.environ.get('mqtt_client_host','')
        self.mqtt_port = int(os.environ.get('mqtt_client_port',''))
        self.mqtt_topic = os.environ.get('mqtt_client_root_topic','')
        self.mqtt_qos = int(os.environ.get('mqtt_qos',''))
        self.mqtt_retain = eval(os.environ.get('mqtt_retain',''))
        
        if eval(os.environ.get('mqtt_auth','')):
            self.mqtt_username = os.environ.get('mqtt_username','')
            self.mqtt_password = os.environ.get('mqtt_password','')

        if eval(os.environ.get('mqtt_auth','')):
            self.mqtt_auth = { "username": os.environ.get('mqtt_username',''), "password": os.environ.get('mqtt_password','') }
        else:
            self.mqtt_auth = None

        self.logger = logger
        logger.info("initialized")


    def run(self):
        self.logger.info("running")
        while True:
            try:
                self.logger.info("loop")
                self.msgs = []
                asyncio.get_event_loop().run_until_complete(self.getWpData())
            except Exception as err:
                if DEBUG:
                    raise
                else:
                    self.logger.error(f"Error while processing item: {self.lastItem}\n{err}\n")
            finally:
                sleep(LOOP_SLEEP)

    def processItem(self, item, path):
        name = item.find("./name").text
        if name is None:
            self.logger.error(f"Error while processing item: item.name is None")
        self.lastItem = name
        name = item.find("./name").text
        name = name.replace("+", ".")
        value = item.find("./value")

        if (value is None):
            children = item.findall("./item")
            for child in children:
                self.processItem(child, f"{path}{name}/")
        else:
            val = value.text
            if val is None:
                self.logger.warn(f"Value is None: {name}")
            else:
                if (val.endswith("°C")):
                    val = val[:-2]
                if (val.endswith(" K")):
                    val = val[:-2]
                if (val.endswith(" l/h")):
                    val = val[:-4]
                if (val.endswith(" V")):
                    val = val[:-2]
                if (val.endswith(" bar")):
                    val = val[:-4]
                if (val.endswith(" kWh")):
                    val = val[:-4]
                if (val.endswith(" kW")):
                    val = val[:-3]
                if (val.endswith(" min")):
                    val = val[:-4]
                if (val.endswith(" h")):
                    val = val[:-2]
                if (val.endswith(" Hz")):
                    val = val[:-3]
                if (val.endswith(" %")):
                    val = val[:-2]
                if (val.endswith("h")):
                    val = val[:-1]
                if (val.endswith("Ein")):
                    val = "CLOSED"
                if (val.endswith("Aus")):
                    val = "OPEN"

                if (name == "Durchfluss" and val.startswith("-")):
                    val = "0"

                msgs = []
                msgs.append({ "topic": f"{self.mqtt_topic}{path}{name}", "payload": val, "qos": self.mqtt_qos, "retain": self.mqtt_retain })
                #self.logger.info(f"Data: {self.mqtt_topic}{path}{name} = {val}")
                publish.multiple(msgs, hostname=self.mqtt_host, port=self.mqtt_port, client_id=self.mqtt_client_id, auth=self.mqtt_auth)

    async def processRoot(self, root, elementName, websocket):
        itemId = root.find(f"./item[name='{elementName}']").attrib["id"]

        await websocket.send(f"GET;{itemId}")
        response = await asyncio.wait_for(websocket.recv(), 10)

        root2 = ET.fromstring(response)
        items = root2.findall("./item")

        for item in items:
            self.processItem(item, f"{elementName}/")

    async def getWpData(self):
        async with websockets.connect(self.luxtronik_url, subprotocols=['Lux_WS']) as websocket:
            await websocket.send(self.luxtronik_login)
            response = await asyncio.wait_for(websocket.recv(), 10)

            root = ET.fromstring(response)

            await self.processRoot(root, "Informationen", websocket)
            await self.processRoot(root, "Einstellungen", websocket)



logging.basicConfig(stream=sys.stdout, format='%(asctime)s: %(name)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)
logger.level = logging.INFO
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.handlers.RotatingFileHandler("/log/wp-mqtt.log", maxBytes=10000000, backupCount=4)
handler.setFormatter(formatter)
logger.addHandler(handler)


# Create daemon object.
d = WpMqtt()
d.init(logger)
d.logger = logger
d.run()
