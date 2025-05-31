# Nosana Node Home Assistant Integration

This integration allows you to monitor the status of a Nosana node in Home Assistant. It creates a sensor entity (`sensor.nosana_node_<first_8_chars>_node_status`) that displays the node's status as "Queued" or "Running" by polling the Nosana API. Additional attributes like uptime, version, country, and network stats are available.

## Features
- Configurable via Home Assistant's UI.
- Displays node status ("Queued" or "Running").
- Provides attributes: `node_address`, `uptime`, `version`, `country`, `ping_ms`, `download_mbps`, `upload_mbps`.
- Updates every 60 seconds.

## Installation

### Via HACS
1. Open HACS in Home Assistant.
2. Go to **Integrations** > **Explore & Download Repositories**.
3. Search for "Nosana Node" or add the repository: `https://github.com/yourusername/nosana_node`.
4. Click **Download** and install the integration.
5. Restart Home Assistant.

### Manual Installation
1. Copy the `custom_components/nosana_node/` folder to your Home Assistant configuration directory (e.g., `~/.homeassistant/custom_components/nosana_node/`).
2. Restart Home Assistant.

## Configuration
1. Go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for and select **Nosana Node**.
3. Enter your Solana node address (e.g., `67qvHLKGmM62RLevcGRde1aWhEPU3njDiemvX6RZEX6i`).
4. Optionally, set a custom name (defaults to "Nosana Node <first_8_chars>").
5. Submit to create the sensor.

The sensor will appear as `sensor.nosana_node_<first_8_chars>_node_status` (e.g., `sensor.nosana_node_67qvHLKG_node_status`).

## Usage
- **Lovelace Card**:
  ```yaml
  type: entities
  entities:
    - entity: sensor.nosana_node_67qvHLKG_node_status
      name: Nosana Node Status
    - type: attribute
      entity: sensor.nosana_node_67qvHLKG_node_status
      attribute: version
      name: Node Version
    - type: attribute
      entity: sensor.nosana_node_67qvHLKG_node_status
      attribute: ping_ms
      name: Ping
  ```
- **Automation**:
  ```yaml
  alias: Notify if Nosana Node is Running
  trigger:
    platform: state
    entity_id: sensor.nosana_node_67qvHLKG_node_status
    to: "Running"
  action:
    service: notify.notify
    data:
      message: "Nosana node is now running!"
  ```

## Notes
- Ensure the Nosana API (`https://<node_address>.node.k8s.prd.nos.ci/node/info`) is accessible. Test with a browser or `curl`.
- If authentication is required, contact the developer to add API key support.
- Report issues at: https://github.com/yourusername/nosana_node/issues

## License
MIT License