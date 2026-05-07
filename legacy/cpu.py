# Эта пустышка была сделана для проверки/теста чтения конфиг файла, работает

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from settings.config_loader import config

def collect_cpu_data():
    interval = config.collection_intervals.get("cpu", 10)
    print(f"Сбор данных CPU запущен с интервалом {interval} секунд...")

collect_cpu_data()