import logging
import paho.mqtt.client as paho_mqtt
from homeassistant.components.sensor import SensorEntity
from homeassistant.components import mqtt
from homeassistant.core import callback
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Configura il sensore dall'entry creato nel config flow."""
    config = config_entry.data
    async_add_entities([MqttWizardSensor(hass, config)], True)

class MqttWizardSensor(SensorEntity):
    """Entità sensore MQTT dinamica."""

    def __init__(self, hass, config):
        self.hass = hass
        self._config = config
        self._attr_name = config.get("sensor_name")
        self._topic = config.get("topic")
        self._is_remote = config.get("is_remote_broker", False)
        self._attr_native_value = None
        self._remote_client = None
        # Genera un ID unico basato sul topic per evitare duplicati
        self._attr_unique_id = f"{DOMAIN}_{config.get('sensor_name')}_{config.get('topic')}"

    async def async_added_to_hass(self):
        """Eseguito quando l'entità viene aggiunta a HA."""
        if self._is_remote:
            await self.hass.async_add_executor_job(self._setup_remote_broker)
        else:
            await self._setup_local_broker()

    async def _setup_local_broker(self):
        """Sottoscrizione tramite l'integrazione MQTT nativa di HA."""
        @callback
        def message_received(msg):
            self._attr_native_value = msg.payload
            self.async_write_ha_state()
            
        await mqtt.async_subscribe(self.hass, self._topic, message_received)

    def _setup_remote_broker(self):
        """Connessione a un broker esterno tramite paho-mqtt."""
        try:
            client_id = f"ha_wizard_{self._attr_name}"
            self._remote_client = paho_mqtt.Client(client_id=client_id)
            
            if self._config.get("username"):
                self._remote_client.username_pw_set(
                    self._config["username"], 
                    self._config.get("password")
                )

            def on_message(client, userdata, msg):
                try:
                    payload = msg.payload.decode("utf-8")
                    self.hass.loop.call_soon_threadsafe(self._update_state, payload)
                except Exception as e:
                    _LOGGER.error("Errore decodifica su %s: %s", self._topic, e)

            self._remote_client.on_message = on_message
            
            self._remote_client.connect(
                self._config["broker"], 
                self._config.get("port", 1883)
            )
            self._remote_client.subscribe(self._topic)
            self._remote_client.loop_start()
            _LOGGER.info("Connesso al broker remoto per il sensore %s", self._attr_name)

        except Exception as e:
            _LOGGER.error("Errore connessione remota per %s: %s", self._attr_name, e)

    def _update_state(self, payload):
        """Aggiorna lo stato in modo thread-safe."""
        self._attr_native_value = payload
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self):
        """Chiusura connessioni alla rimozione del sensore."""
        if self._remote_client:
            await self.hass.async_add_executor_job(self._remote_client.loop_stop)
            await self.hass.async_add_executor_job(self._remote_client.disconnect)
            _LOGGER.info("Connessione remota chiusa per %s", self._attr_name)