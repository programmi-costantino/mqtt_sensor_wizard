import voluptuous as vol
import paho.mqtt.client as paho_mqtt
from paho.mqtt.enums import CallbackAPIVersion
from homeassistant import config_entries
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.helpers import selector
from homeassistant.core import callback
from .const import DOMAIN

def test_mqtt_connection(broker, port, user, pwd):
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

class MqttWizardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il flusso di configurazione per MQTT Sensor Wizard."""
    VERSION = 1

    def __init__(self):
        self.sensor_data = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Restituisce il gestore delle opzioni (OptionsFlow)."""
        return MqttWizardOptionsFlow()

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
                test_mqtt_connection,
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
            # Converte la stringa "none" della UI in un reale valore None per Python
            if user_input.get("device_class") == "none":
                user_input["device_class"] = None
            if user_input.get("state_class") == "none":
                user_input["state_class"] = None

            self.sensor_data.update(user_input)
            return self.async_create_entry(
                title=self.sensor_data["sensor_name"], 
                data=self.sensor_data
            )

        device_classes = ["none"] + sorted([cls.value for cls in SensorDeviceClass])
        state_classes = ["none"] + sorted([cls.value for cls in SensorStateClass])

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema({
                vol.Optional("template"): str,
                vol.Optional("device_class", default="none"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=device_classes,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("state_class", default="none"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=state_classes,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional("unit_of_measurement"): str,
            })
        )

    async def async_step_import(self, import_data):
        """Gestisce l'importazione da configuration.yaml."""
        unique_id = f"{DOMAIN}_{import_data.get('sensor_name')}_{import_data.get('topic')}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=import_data["sensor_name"], data=import_data)

class MqttWizardOptionsFlow(config_entries.OptionsFlow):
    """Gestisce la modifica delle opzioni dopo l'installazione."""

    def __init__(self):
        self.options_data = {}

    async def async_step_init(self, user_input=None):
        """Mostra il form delle opzioni."""
        current_config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            self.options_data.update(user_input)
            if user_input.get("is_remote_broker"):
                return await self.async_step_remote()
            else:
                if self.options_data.get("device_class") == "none":
                    self.options_data["device_class"] = None
                if self.options_data.get("state_class") == "none":
                    self.options_data["state_class"] = None
                return self.async_create_entry(title="", data=self.options_data)
        
        device_classes = ["none"] + sorted([cls.value for cls in SensorDeviceClass])
        state_classes = ["none"] + sorted([cls.value for cls in SensorStateClass])

        schema = {}
        schema[vol.Optional("is_remote_broker", default=current_config.get("is_remote_broker", False))] = bool
        
        if current_config.get("template") is not None:
            schema[vol.Optional("template", default=current_config.get("template"))] = str
        else:
            schema[vol.Optional("template")] = str

        schema[vol.Optional("device_class", default=current_config.get("device_class") or "none")] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=device_classes, mode=selector.SelectSelectorMode.DROPDOWN)
        )
        schema[vol.Optional("state_class", default=current_config.get("state_class") or "none")] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=state_classes, mode=selector.SelectSelectorMode.DROPDOWN)
        )

        if current_config.get("unit_of_measurement") is not None:
            schema[vol.Optional("unit_of_measurement", default=current_config.get("unit_of_measurement"))] = str
        else:
            schema[vol.Optional("unit_of_measurement")] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))

    async def async_step_remote(self, user_input=None):
        """Mostra il form per il broker remoto se selezionato."""
        errors = {}
        current_config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            success = await self.hass.async_add_executor_job(
                test_mqtt_connection,
                user_input["broker"],
                user_input["port"],
                user_input.get("username"),
                user_input.get("password")
            )
            if success:
                self.options_data.update(user_input)
                if self.options_data.get("device_class") == "none":
                    self.options_data["device_class"] = None
                if self.options_data.get("state_class") == "none":
                    self.options_data["state_class"] = None
                return self.async_create_entry(title="", data=self.options_data)
            errors["base"] = "cannot_connect"

        schema = {}
        schema[vol.Required("broker", default=current_config.get("broker", ""))] = str
        schema[vol.Required("port", default=current_config.get("port", 1883))] = int
        if current_config.get("username") is not None:
            schema[vol.Optional("username", default=current_config.get("username"))] = str
        else:
            schema[vol.Optional("username")] = str
        if current_config.get("password") is not None:
            schema[vol.Optional("password", default=current_config.get("password"))] = str
        else:
            schema[vol.Optional("password")] = str

        return self.async_show_form(step_id="remote", data_schema=vol.Schema(schema), errors=errors)