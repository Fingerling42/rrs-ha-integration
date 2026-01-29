DOMAIN = "robonomics_report_service"
PROBLEM_REPORT_SERVICE = "send_problem_report"
ERROR_SOURCES_MANAGER = "error_sources_manages"
STORAGE_NAME = "integrator_storage"

CONF_PINATA_SECRET = "pinata_secret"
CONF_PINATA_PUBLIC = "pinata_public"
CONF_SENDER_SEED = "sender_seed"

PROBLEM_SERVICE_ROBONOMICS_ADDRESS = "problem_service_robonomics_address"
OWNER_ADDRESS = "subscription_owner_robonomics_address"

ROBONOMICS_WSS = [
    "wss://polkadot.rpc.robonomics.network/",
]

RRS_REPORT_TEMP_DIR = "rrs_report_temp_dir"
LOG_FILE_NAME = "home-assistant.log"
TRACES_FILE_NAME = ".storage/trace.saved_traces"
LOGS_MAX_BYTES = 3 * 1024 * 1024

CHECK_ENTITIES_TIMEOUT = 24 * 60    # Mins
CHECK_LOGS_TIMEOUT = 5         # Mins
