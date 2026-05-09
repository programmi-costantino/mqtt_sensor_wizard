# MQTT Sensor Wizard

## ⚠️ Disclaimer: AI Generated

**[IT]** 
Questo progetto è stato realizzato con il supporto dell'Intelligenza Artificiale. Non avendo una conoscenza approfondita di Python e delle logiche interne per lo sviluppo di *custom components* su Home Assistant, mi sono affidato all'IA per la stesura del codice. Potrebbe non seguire tutte le "best practice" ufficiali. Qualsiasi suggerimento, revisione del codice o Pull Request è assolutamente ben accetto!

**[EN]**
This project was created with the help of Artificial Intelligence. Since I don't have deep knowledge of Python and Home Assistant *custom components* development, I relied on AI to write the code. It might not follow all the official best practices. Any suggestions, code reviews, or Pull Requests are highly appreciated!

---

## ✨ Features / Funzionalità

**[IT]**
* **Configurazione via UI**: Crea sensori MQTT direttamente dall'interfaccia utente (Config Flow) senza dover toccare il file `configuration.yaml`.
* **Supporto Multi-Broker**: Utilizza il broker MQTT nativo di Home Assistant oppure collegati a broker remoti/esterni (con supporto per username e password).
* **Template Jinja2**: Estrai facilmente dati complessi dai tuoi payload MQTT (es. JSON) utilizzando i template nativi di Home Assistant (es. `{{ value_json.temperatura }}`).
* **Classi Native**: Imposta facilmente *Device Class*, *State Class* e *Unità di Misura* per abilitare i grafici storici e le statistiche a lungo termine di Home Assistant.
* **Modifica a Caldo (Options Flow)**: Modifica i template, le classi o le credenziali del broker remoto in qualsiasi momento tramite il pulsante "Configura", senza dover cancellare e ricreare il sensore.

**[EN]**
* **UI Configuration**: Create MQTT sensors directly from the user interface (Config Flow) without touching the `configuration.yaml` file.
* **Multi-Broker Support**: Use Home Assistant's native MQTT broker or connect to remote/external brokers (with username and password support).
* **Jinja2 Templates**: Easily extract complex data from your MQTT payloads (e.g. JSON) using Home Assistant's native templating engine (e.g. `{{ value_json.temperature }}`).
* **Native Classes**: Easily set *Device Class*, *State Class*, and *Unit of Measurement* to enable Home Assistant's history graphs and long-term statistics.
* **Hot Editing (Options Flow)**: Modify templates, classes, or remote broker credentials at any time via the "Configure" button, without having to delete and recreate the sensor.
