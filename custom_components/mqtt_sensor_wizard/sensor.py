import logging
import json
import paho.mqtt.client as paho_mqtt
from paho.mqtt.enums import CallbackAPIVersion
from homeassistant.components.sensor import SensorEntity
from homeassistant.components import mqtt
from homeassistant.core import callback
from homeassistant.helpers.template import Template
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configura il sensore dall'entry creato nel config flow."""
    config = config_entry.data
    async_add_entities([MqttWizardSensor(hass, config)], True)

class MqttWizardSensor(SensorEntity):
    """Sensore MQTT con supporto a Template e Classi native."""

    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = config.get("sensor_name")
        self._topic = config.get("topic")
        self._is_remote = config.get("is_remote_broker", False)
        
        template_str = config.get("template")
        if template_str and "<value>" in template_str:
            template_str = template_str.replace("<value>", "{{ value }}")
            
        if template_str:
            self._template = Template(template_str, self.hass)
        else:
            self._template = None
        self._attr_device_class = config.get("device_class")
        self._attr_state_class = config.get("state_class")
        self._attr_native_unit_of_measurement = config.get("unit_of_measurement")
        self._attr_native_value = None
        self._remote_client = None
        self._unsubscribe_local = None
        self._attr_unique_id = f"{DOMAIN}_{config.get('sensor_name')}_{config.get('topic')}"

    async def async_added_to_hass(self):
        """Eseguito quando l'entità viene aggiunta a HA."""
        if self._is_remote:
            await self.hass.async_add_executor_job(self._setup_remote_broker)
        else:
            await self._setup_local_broker()

    async def _setup_local_broker(self):
        """Sottoscrizione tramite integrazione MQTT nativa."""
        @callback
        def message_received(msg):
            self._update_state(msg.payload)
        self._unsubscribe_local = await mqtt.async_subscribe(self.hass, self._topic, message_received)

    def _setup_remote_broker(self):
        """Connessione a broker esterno (paho-mqtt 2.x)."""
        try:
            client_id = f"ha_wizard_{self._attr_name}"
            self._remote_client = paho_mqtt.Client(CallbackAPIVersion.VERSION1, client_id=client_id)
            if self._config.get("username"):
                self._remote_client.username_pw_set(self._config["username"], self._config.get("password"))
            def on_message(client, userdata, msg):
                payload = msg.payload.decode("utf-8")
                self.hass.loop.call_soon_threadsafe(self._update_state, payload)
            self._remote_client.on_message = on_message
            self._remote_client.connect(self._config["broker"], self._config.get("port", 1883))
            self._remote_client.subscribe(self._topic)
            self._remote_client.loop_start()
        except Exception as e:
            _LOGGER.error("Errore remoto %s: %s", self._attr_name, e)

    def _update_state(self, payload):
        """Valuta il template Jinja2 e aggiorna HA."""
        try:
            val = str(payload)
            if self._template is not None:
                variables = {"value": val}
                # Se il payload è un JSON, permettiamo l'uso di value_json nel template
                try:
                    variables["value_json"] = json.loads(val)
                except Exception:
                    pass
                
                self._attr_native_value = self._template.async_render(variables=variables, parse_result=True)
            else:
                self._attr_native_value = val
                
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Errore template su %s: %s", self._attr_name, e)

    async def async_will_remove_from_hass(self):
        """Pulizia alla rimozione del sensore."""
        if self._remote_client:
            await self.hass.async_add_executor_job(self._remote_client.loop_stop)
            await self.hass.async_add_executor_job(self._remote_client.disconnect)
        if self._unsubscribe_local:
            self._unsubscribe_local()