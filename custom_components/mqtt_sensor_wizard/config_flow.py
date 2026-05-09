import voluptuous as vol
import paho.mqtt.client as paho_mqtt
from paho.mqtt.enums import CallbackAPIVersion
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from .const import DOMAIN

class MqttWizardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione per MQTT Sensor Wizard."""
    VERSION = 1

    def __init__(self):
        self.sensor_data = {}

    async def async_step_user(self, user_input=None):
        """Primo step: Dati base del sensore."""
        if user_input is not None:
            unique_id = f"{DOMAIN}_{user_input.get('sensor_name')}_{user_input.get('topic')}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            self.sensor_data.update(user_input)
            if user_input.get("is_remote_broker"):
                return await self.async_step_remote()
            return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("sensor_name"): str,
                vol.Required("topic"): str,
                vol.Optional("is_remote_broker", default=False): bool,
            })
        )

    async def async_step_remote(self, user_input=None):
        """Secondo step: Configurazione broker remoto."""
        errors = {}
        if user_input is not None:
            success = await self.hass.async_add_executor_job(
                self._test_mqtt_connection,
                user_input["broker"],
                user_input["port"],
                user_input.get("username"),
                user_input.get("password")
            )
            if success:
                self.sensor_data.update(user_input)
                return await self.async_step_options()
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

    async def async_step_options(self, user_input=None):
        """Terzo step: Template e Classi del sensore."""
        if user_input is not None:
            self.sensor_data.update(user_input)
            return self.async_create_entry(
                title=self.sensor_data["sensor_name"], 
                data=self.sensor_data
            )

        device_classes = [None] + sorted([cls.value for cls in SensorDeviceClass])
        state_classes = [None] + sorted([cls.value for cls in SensorStateClass])

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Optional("template", default="<value>"): str,
                vol.Optional("device_class"): vol.In(device_classes),
                vol.Optional("state_class"): vol.In(state_classes),
                vol.Optional("unit_of_measurement"): str,
            })
        )

    async def async_step_import(self, import_data):
        """Gestisce l'importazione da configuration.yaml."""
        unique_id = f"{DOMAIN}_{import_data.get('sensor_name')}_{import_data.get('topic')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=import_data["sensor_name"], data=import_data)

    def _test_mqtt_connection(self, broker, port, user, pwd):
        """Validazione broker remoto (paho-mqtt 2.x)."""
        client = paho_mqtt.Client(CallbackAPIVersion.VERSION1) 
        if user:
            client.username_pw_set(user, pwd)
        try:
            client.connect(broker, port, keepalive=5)
            client.disconnect()
            return True
        except Exception:
            return False