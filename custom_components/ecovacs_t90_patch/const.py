"""Constants for the Ecovacs T90 Pro CN patch."""

DOMAIN = "ecovacs_t90_patch"
ECOVACS_DOMAIN = "ecovacs"
TARGET_DEVICE_CLASS = "guaexd"
SOURCE_HARDWARE_MODULE = "deebot_client.hardware.twunby"
INTEGRATION_VERSION = "1.0.6"

CARD_STATIC_URL = "/ecovacs_t90_patch"
CARD_FILENAME = "ecovacs-t90-map-card.js"
CARD_MODULE_URL = f"{CARD_STATIC_URL}/{CARD_FILENAME}?v={INTEGRATION_VERSION}"

DATA_STATIC_PATH_REGISTERED = "static_path_registered"
DATA_EXTRA_CARD_REGISTERED = "extra_card_registered"
