DOMAIN = "robonomics_report_service"

PROBLEM_REPORT_SERVICE = "send_problem_report"
CONF_EMAIL = "conf_email"

STORAGE_NAME = "integrator_storage"

CONF_PINATA_SECRET = "pinata_secret"
CONF_PINATA_PUBLIC = "pinata_public"
CONF_SENDER_SEED = "sender_seed"

ROBONOMICS_WSS = [
    "wss://polkadot.rpc.robonomics.network/",
]

LOG_FILE_NAME = "home-assistant.log"
TRACES_FILE_NAME = ".storage/trace.saved_traces"
IPFS_PROBLEM_REPORT_FOLDER = "ha_problem_report"
LOGS_MAX_LEN = 3 * 1024 * 1024

PROBLEM_SERVICE_ROBONOMICS_ADDRESS = "problem_service_robonomics_address"

CHECK_ENTITIES_TIMEOUT = 24  # Hours

OWNER_ADDRESS = PROBLEM_SERVICE_ROBONOMICS_ADDRESS
ERROR_SOURCES_MANAGER = "error_sources_manages"
