import voluptuous as vol
import paho.mqtt.client as paho_mqtt
from paho.mqtt.enums import CallbackAPIVersion
from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

class MqttWizardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione per MQTT Sensor Wizard."""
    VERSION = 1

    def __init__(self):
        """Inizializza i dati temporanei per il flusso a più step."""
        self.sensor_data = {}

    async def async_step_user(self, user_input=None):
        """Primo step: Nome del sensore, Topic e scelta del Broker."""
        if user_input is not None:
            self.sensor_data.update(user_input)
            if user_input.get("is_remote_broker"):
                return await self.async_step_remote()
            else:
                return self.async_create_entry(
                    title=self.sensor_data["sensor_name"], 
                    data=self.sensor_data
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("sensor_name"): str,
                vol.Required("topic"): str,
                vol.Optional("is_remote_broker", default=False): bool,
            })
        )

    async def async_step_remote(self, user_input=None):
        """Secondo step: Dati di connessione del broker remoto con validazione."""
        errors = {}
        if user_input is not None:
            # Test di connessione compatibile con paho-mqtt 2.x
            success = await self.hass.async_add_executor_job(
                self._test_mqtt_connection,
                user_input["broker"],
                user_input["port"],
                user_input.get("username"),
                user_input.get("password")
            )

            if success:
                self.sensor_data.update(user_input)
                return self.async_create_entry(
                    title=self.sensor_data["sensor_name"], 
                    data=self.sensor_data
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="remote",
            data_schema=vol.Schema({
                vol.Required("broker"): str,
                vol.Required("port", default=1883): int,
                vol.Optional("username"): str,
                vol.Optional("password"): str,
            }),
            errors=errors
        )

    async def async_step_import(self, import_data):
        """Gestisce l'importazione automatica da configuration.yaml."""
        unique_id = f"{DOMAIN}_{import_data.get('sensor_name')}_{import_data.get('topic')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        
        return self.async_create_entry(
            title=import_data["sensor_name"], 
            data=import_data
        )

    def _test_mqtt_connection(self, broker, port, user, pwd):
        """Funzione di test per validare le credenziali (paho-mqtt 2.x)."""
        client = paho_mqtt.Client(CallbackAPIVersion.VERSION1) 
        if user:
            client.username_pw_set(user, pwd)
        try:
            client.connect(broker, port, keepalive=5)
            client.disconnect()
            return True
        except Exception:
            return False