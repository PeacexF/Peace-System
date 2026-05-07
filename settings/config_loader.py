import json
import os

class Config:
    def __init__(self):

        base_path = os.path.dirname(__file__) 
        config_path = os.path.join(base_path, "config.json")    # Ищем конфиг

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Конфигурационный файл {config_path} не найден!")
        
        with open(config_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)   # Грузим JSON в словарь

    # Добавляем свойста к различным отделам JSON конфига, сильно упрощает доступ к нужным данным
    @property
    def collection_intervals(self):
        return self._data.get("collection_intervals", {})

    @property
    def anomaly_thresholds(self):
        return self._data.get("anomaly_thresholds", {})

    @property
    def storage(self):
        return self._data.get("storage", {})

    @property
    def logging(self):
        return self._data.get("logging", {})

config = Config()