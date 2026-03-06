DOMAIN = "robonomics_report_service"
PROBLEM_REPORT_SERVICE = "send_problem_report"
ERROR_WATCHERS_MANAGER = "error_watchers_manager"

CREDS_STORAGE_KEY = "creds_storage"

CONF_PINATA_SECRET = "pinata_secret"
CONF_PINATA_PUBLIC = "pinata_public"
CONF_SENDER_SEED = "sender_seed"
CONF_SENDER_EMAIL = "sender_email"
CONF_NETWORK = "network"

PROBLEM_SERVICE_ROBONOMICS_ADDRESS = "problem_service_robonomics_address"
OWNER_ADDRESS = "subscription_owner_robonomics_address"

NETWORK_POLKADOT = "polkadot"
NETWORK_KUSAMA = "kusama"
DEFAULT_NETWORK = NETWORK_POLKADOT

NETWORK_WSS = {
    NETWORK_POLKADOT: [
        "wss://polkadot.rpc.robonomics.network/",
    ],
    NETWORK_KUSAMA: [
        "wss://kusama.rpc.robonomics.network/",
    ],
}

RRS_REPORT_TEMP_DIR = "rrs_report_temp_dir"
LOG_FILE_NAME = "home-assistant.log"
TRACES_FILE_NAME = ".storage/trace.saved_traces"
LOGS_MAX_BYTES = 3 * 1024 * 1024

CHECK_LOGS_TIMEOUT = 24 * 60        # Mins
CHECK_ENTITIES_TIMEOUT = 24 * 60    # Mins
