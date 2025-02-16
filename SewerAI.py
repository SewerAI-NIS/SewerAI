import serial
import customtkinter as ctk
import threading
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Подключение к Arduino
try:
    ser = serial.Serial("COM10", 9600, timeout=1)
    time.sleep(2)  # Ожидание соединения
except serial.SerialException:
    print("Ошибка: Не удалось подключиться к Arduino!")
    ser = None

# Глобальные переменные
data = []  # Данные о расстоянии
positions = []  # Координаты трубы
clean_pipe_data = []  # Эталонные данные (чистая труба)
learning_phase = False  # Флаг обучения
analysis_phase = False  # Флаг анализа трубы
pipe_length = 30  # Длина трубы в см
sensor_step = 1  # Шаг измерения в см
log_entries = []  # Лог событий

def detect_blockage():
    if len(data) < len(clean_pipe_data) or not analysis_phase:
        return None
    differences = [abs(data[i] - clean_pipe_data[i]) for i in range(len(clean_pipe_data))]
    max_deviation = max(differences)
    if max_deviation > 5:
        blockage_index = differences.index(max_deviation)
        blockage_position = positions[blockage_index] if blockage_index < len(positions) else 0
        log_entries.append(f"Засор на {blockage_position} см")
        return blockage_position
    return None

def read_sensor():
    global learning_phase, analysis_phase
    current_position = 0
    while True:
        try:
            if ser and ser.in_waiting > 0:
                line = ser.readline().decode("utf-8").strip()
                if line.startswith("Distance:"):
                    distance = int(line.split(":")[1].strip().replace("cm", ""))
                    if learning_phase:
                        clean_pipe_data.append(distance)
                    elif analysis_phase:
                        data.append(distance)
                        positions.append(current_position)
                        current_position += sensor_step
                        blockage = detect_blockage()
                        if blockage is not None:
                            app.update_log(f"⚠️ Засор обнаружен на {blockage} см!")
        except Exception as e:
            print(f"Ошибка при чтении: {e}")
        time.sleep(0.5)

class MonitoringApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        self.root = ctk.CTk()
        self.root.title("Мониторинг канализации")
        self.root.geometry("800x600")
        self.create_interface()
        self.update_plot()

    def create_interface(self):
        self.label = ctk.CTkLabel(self.root, text="Мониторинг засоров", font=("Arial", 18, "bold"))
        self.label.pack(pady=10)
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(expand=True, fill="both")
        self.create_monitoring_tab()
        self.create_settings_tab()
        self.create_logs_tab()

    def create_monitoring_tab(self):
        tab = self.tabview.add("Мониторинг")
        self.start_button = ctk.CTkButton(tab, text="Начать обучение", command=self.start_learning)
        self.start_button.pack(pady=5)
        self.end_button = ctk.CTkButton(tab, text="Закончить обучение", command=self.end_learning)
        self.end_button.pack(pady=5)
        self.analyze_button = ctk.CTkButton(tab, text="Анализ трубы", command=self.start_analysis)
        self.analyze_button.pack(pady=5)
        self.figure, self.ax = plt.subplots(figsize=(6, 3))
        self.canvas = FigureCanvasTkAgg(self.figure, master=tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def create_settings_tab(self):
        tab = self.tabview.add("Настройки")
        self.com_port_entry = ctk.CTkEntry(tab, placeholder_text="Введите COM-порт")
        self.com_port_entry.pack(pady=10)
        self.save_button = ctk.CTkButton(tab, text="Сохранить", command=self.save_settings)
        self.save_button.pack(pady=5)

    def create_logs_tab(self):
        tab = self.tabview.add("Журнал")
        self.log_text = ctk.CTkTextbox(tab, height=200)
        self.log_text.pack(pady=10, fill="both", expand=True)
        self.clear_logs_button = ctk.CTkButton(tab, text="Очистить журнал", command=self.clear_logs)
        self.clear_logs_button.pack(pady=5)

    def start_learning(self):
        global learning_phase, clean_pipe_data, data, positions, analysis_phase
        learning_phase = True
        analysis_phase = False
        clean_pipe_data.clear()
        data.clear()
        positions.clear()
        self.update_log("Начато обучение!")

    def end_learning(self):
        global learning_phase
        learning_phase = False
        self.update_log("Обучение завершено!")

    def start_analysis(self):
        global analysis_phase, data, positions
        if not clean_pipe_data:
            self.update_log("Ошибка: сначала завершите обучение!")
            return
        analysis_phase = True
        data.clear()
        positions.clear()
        self.update_log("Анализ трубы запущен...")

    def save_settings(self):
        port = self.com_port_entry.get()
        self.update_log(f"Сохранен COM-порт: {port}")

    def clear_logs(self):
        self.log_text.delete("1.0", "end")

    def update_log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def update_plot(self):
        self.ax.clear()
        if len(data) > 1:
            self.ax.plot(positions, data, color="blue", linewidth=2, label="Текущие данные")
            if len(clean_pipe_data) > 1:
                self.ax.plot(range(len(clean_pipe_data)), clean_pipe_data, color="green", linestyle="--", label="Эталонные данные")
            self.ax.legend()
            self.ax.grid(True)
        self.canvas.draw()
        self.root.after(500, self.update_plot)

    def run(self):
        threading.Thread(target=read_sensor, daemon=True).start()
        self.root.mainloop()

if __name__ == "__main__":
    app = MonitoringApp()
    app.run()
