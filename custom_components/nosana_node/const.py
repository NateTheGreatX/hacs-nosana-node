# custom_components/nosana_node/const.py
"""Constants for the Nosana Node integration."""

DOMAIN = "nosana_node"
CONF_NODE_ADDRESS = "node_address"

# Deployer addresses that are treated as "General" deployments. Jobs triggered
# by these deployers report a job type of "General". Any other deployer reports
# a job type of "Deployment Manager".
CONF_GENERAL_DEPLOYMENTS = "general_deployments"
DEFAULT_GENERAL_DEPLOYMENTS = ["JBksZBRkyjPYnqmnxheMr4t1WP88gAwGX6SUz3HuPkfT"]