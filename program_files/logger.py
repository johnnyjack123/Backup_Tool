import logging

logger = logging.getLogger("my_backup_logger")
logger.setLevel(logging.INFO)

# File Handler für Datei-Ausgabe konfigurieren
file_handler = logging.FileHandler("backup_tool.log")
file_handler.setLevel(logging.INFO)

# Format für Logs definieren
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)

# Handler dem Logger hinzufügen
logger.addHandler(file_handler)
