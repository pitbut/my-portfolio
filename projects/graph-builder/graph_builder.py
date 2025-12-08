"""
Интерактивный построитель графиков
Автор: Pit
Описание: Программа для построения графиков с ручным добавлением точек
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
from scipy.interpolate import interp1d, make_interp_spline
import os

class GraphBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("Построитель графиков")
        self.root.geometry("1400x800")
        
        # Данные для графиков
        self.curves = []  # Список кривых [{points: [(x,y)], color: str, line_style: str, marker: str, label: str, show_points: bool}]
        self.current_curve_index = None
        self.mode = "add"  # режимы: add, delete, move, draw_func
        
        # Параметры графика
        self.x_label = "X"
        self.y_label = "Y"
        self.x_max = 10
        self.y_max = 10
        self.grid_enabled = True
        self.grid_step_x = 1
        self.grid_step_y = 1
        
        self.setup_ui()
        self.create_plot()
        
    def setup_ui(self):
        """Создание интерфейса"""
        
        # ===== ЛЕВАЯ ПАНЕЛЬ - Настройки с прокруткой =====
        left_panel_container = tk.Frame(self.root, width=350, bg='#f0f0f0')
        left_panel_container.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        # Создаем canvas для прокрутки
        canvas = tk.Canvas(left_panel_container, bg='#f0f0f0', width=330)
        scrollbar = tk.Scrollbar(left_panel_container, orient="vertical", command=canvas.yview)
        
        # Создаем фрейм внутри canvas
        left_panel = tk.Frame(canvas, bg='#f0f0f0')
        
        # Настраиваем прокрутку
        left_panel.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=left_panel, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Упаковываем canvas и scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязываем прокрутку колесом мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # --- Начальные настройки ---
        settings_frame = tk.LabelFrame(left_panel, text="Начальные настройки", font=('Arial', 10, 'bold'))
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Количество кривых
        tk.Label(settings_frame, text="Количество кривых:").grid(row=0, column=0, sticky='w', padx=5, pady=3)
        self.num_curves_var = tk.StringVar(value="1")
        tk.Entry(settings_frame, textvariable=self.num_curves_var, width=10).grid(row=0, column=1, padx=5, pady=3)
        tk.Button(settings_frame, text="Создать кривые", command=self.create_curves).grid(row=0, column=2, padx=5, pady=3)
        
        # Легенда осей
        tk.Label(settings_frame, text="Подпись оси X:").grid(row=1, column=0, sticky='w', padx=5, pady=3)
        self.x_label_var = tk.StringVar(value="X")
        tk.Entry(settings_frame, textvariable=self.x_label_var, width=20).grid(row=1, column=1, columnspan=2, padx=5, pady=3)
        
        tk.Label(settings_frame, text="Подпись оси Y:").grid(row=2, column=0, sticky='w', padx=5, pady=3)
        self.y_label_var = tk.StringVar(value="Y")
        tk.Entry(settings_frame, textvariable=self.y_label_var, width=20).grid(row=2, column=1, columnspan=2, padx=5, pady=3)
        
        # Максимальные значения осей
        tk.Label(settings_frame, text="Максимум X:").grid(row=3, column=0, sticky='w', padx=5, pady=3)
        self.x_max_var = tk.StringVar(value="10")
        tk.Entry(settings_frame, textvariable=self.x_max_var, width=10).grid(row=3, column=1, padx=5, pady=3)
        
        tk.Label(settings_frame, text="Максимум Y:").grid(row=4, column=0, sticky='w', padx=5, pady=3)
        self.y_max_var = tk.StringVar(value="10")
        tk.Entry(settings_frame, textvariable=self.y_max_var, width=10).grid(row=4, column=1, padx=5, pady=3)
        
        # Сетка
        tk.Label(settings_frame, text="Шаг сетки X:").grid(row=5, column=0, sticky='w', padx=5, pady=3)
        self.grid_x_var = tk.StringVar(value="1")
        tk.Entry(settings_frame, textvariable=self.grid_x_var, width=10).grid(row=5, column=1, padx=5, pady=3)
        
        tk.Label(settings_frame, text="Шаг сетки Y:").grid(row=6, column=0, sticky='w', padx=5, pady=3)
        self.grid_y_var = tk.StringVar(value="1")
        tk.Entry(settings_frame, textvariable=self.grid_y_var, width=10).grid(row=6, column=1, padx=5, pady=3)
        
        self.grid_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Показать сетку", variable=self.grid_enabled_var).grid(row=7, column=0, columnspan=2, sticky='w', padx=5, pady=3)
        
        tk.Button(settings_frame, text="Применить настройки", command=self.apply_settings, bg='#4CAF50', fg='white').grid(row=8, column=0, columnspan=3, pady=5)
        
        # --- Список кривых ---
        curves_frame = tk.LabelFrame(left_panel, text="Кривые", font=('Arial', 10, 'bold'))
        curves_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Список
        self.curves_listbox = tk.Listbox(curves_frame, height=8)
        self.curves_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.curves_listbox.bind('<<ListboxSelect>>', self.on_curve_select)
        
        # --- Настройки текущей кривой ---
        curve_settings_frame = tk.LabelFrame(left_panel, text="Настройки текущей кривой", font=('Arial', 10, 'bold'))
        curve_settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Название кривой
        tk.Label(curve_settings_frame, text="Название:").grid(row=0, column=0, sticky='w', padx=5, pady=3)
        self.curve_label_var = tk.StringVar()
        tk.Entry(curve_settings_frame, textvariable=self.curve_label_var, width=20).grid(row=0, column=1, columnspan=2, padx=5, pady=3)
        
        # Цвет линии
        tk.Label(curve_settings_frame, text="Цвет линии:").grid(row=1, column=0, sticky='w', padx=5, pady=3)
        self.line_color_var = tk.StringVar(value="blue")
        colors = ["blue", "red", "green", "black", "orange", "purple", "brown", "pink"]
        ttk.Combobox(curve_settings_frame, textvariable=self.line_color_var, values=colors, width=17).grid(row=1, column=1, columnspan=2, padx=5, pady=3)
        
        # Стиль линии
        tk.Label(curve_settings_frame, text="Стиль линии:").grid(row=2, column=0, sticky='w', padx=5, pady=3)
        self.line_style_var = tk.StringVar(value="solid")
        styles = [("Сплошная", "solid"), ("Штриховая", "dashed"), ("Штрихпунктирная", "dashdot"), ("Точечная", "dotted")]
        style_names = [s[0] for s in styles]
        style_combo = ttk.Combobox(curve_settings_frame, values=style_names, width=17)
        style_combo.grid(row=2, column=1, columnspan=2, padx=5, pady=3)
        style_combo.current(0)
        style_combo.bind('<<ComboboxSelected>>', lambda e: self.line_style_var.set(styles[style_combo.current()][1]))
        
        # Маркер точек
        tk.Label(curve_settings_frame, text="Форма точек:").grid(row=3, column=0, sticky='w', padx=5, pady=3)
        self.marker_var = tk.StringVar(value="o")
        markers = [("Круг", "o"), ("Квадрат", "s"), ("Треугольник", "^"), ("Ромб", "D"), ("Звезда", "*"), ("Крест", "x")]
        marker_names = [m[0] for m in markers]
        marker_combo = ttk.Combobox(curve_settings_frame, values=marker_names, width=17)
        marker_combo.grid(row=3, column=1, columnspan=2, padx=5, pady=3)
        marker_combo.current(0)
        marker_combo.bind('<<ComboboxSelected>>', lambda e: self.marker_var.set(markers[marker_combo.current()][1]))
        
        # Показывать точки
        self.show_points_var = tk.BooleanVar(value=True)
        tk.Checkbutton(curve_settings_frame, text="Показывать точки", variable=self.show_points_var).grid(row=4, column=0, columnspan=2, sticky='w', padx=5, pady=3)
        
        tk.Button(curve_settings_frame, text="Применить к кривой", command=self.update_curve_settings, bg='#2196F3', fg='white').grid(row=5, column=0, columnspan=3, pady=5)
        
        # --- Режимы работы ---
        modes_frame = tk.LabelFrame(left_panel, text="Режимы работы", font=('Arial', 10, 'bold'))
        modes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.mode_var = tk.StringVar(value="add")
        tk.Radiobutton(modes_frame, text="Добавить точку", variable=self.mode_var, value="add", command=self.change_mode).pack(anchor='w', padx=5)
        tk.Radiobutton(modes_frame, text="Удалить точку", variable=self.mode_var, value="delete", command=self.change_mode).pack(anchor='w', padx=5)
        tk.Radiobutton(modes_frame, text="Переместить точку", variable=self.mode_var, value="move", command=self.change_mode).pack(anchor='w', padx=5)
        
        # Кнопка очистки кривой
        tk.Button(modes_frame, text="🗑️ Очистить текущую кривую", command=self.clear_current_curve, bg='#f44336', fg='white').pack(fill=tk.X, padx=5, pady=5)
        
        # Сглаживание
        tk.Button(modes_frame, text="📈 Сгладить кривую", command=self.smooth_curve, bg='#FF9800', fg='white').pack(fill=tk.X, padx=5, pady=5)
        
        # Построение по формуле
        formula_frame = tk.LabelFrame(modes_frame, text="Построение по формуле")
        formula_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(formula_frame, text="Формула (y=):").pack(anchor='w', padx=5)
        self.formula_var = tk.StringVar(value="x**2")
        tk.Entry(formula_frame, textvariable=self.formula_var).pack(fill=tk.X, padx=5)
        
        # Параметры построения
        params_frame = tk.Frame(formula_frame)
        params_frame.pack(fill=tk.X, padx=5, pady=3)
        tk.Label(params_frame, text="Количество точек:").pack(side=tk.LEFT)
        self.formula_points_var = tk.StringVar(value="50")
        tk.Entry(params_frame, textvariable=self.formula_points_var, width=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(formula_frame, text="Построить по формуле", command=self.build_from_formula, bg='#9C27B0', fg='white').pack(fill=tk.X, padx=5, pady=3)
        tk.Label(formula_frame, text="После построения можно\nредактировать точки вручную", font=('Arial', 8), fg='gray').pack(padx=5, pady=3)
        
        # --- Экспорт и печать ---
        export_frame = tk.LabelFrame(left_panel, text="Экспорт графика", font=('Arial', 10, 'bold'))
        export_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Button(export_frame, text="💾 Сохранить как PNG", command=lambda: self.save_graph('png'), bg='#4CAF50', fg='white').pack(fill=tk.X, padx=5, pady=3)
        tk.Button(export_frame, text="💾 Сохранить как PDF", command=lambda: self.save_graph('pdf'), bg='#4CAF50', fg='white').pack(fill=tk.X, padx=5, pady=3)
        tk.Button(export_frame, text="💾 Сохранить как SVG", command=lambda: self.save_graph('svg'), bg='#4CAF50', fg='white').pack(fill=tk.X, padx=5, pady=3)
        tk.Button(export_frame, text="🖨️ Распечатать", command=self.print_graph, bg='#2196F3', fg='white').pack(fill=tk.X, padx=5, pady=3)
        
        # ===== ПРАВАЯ ЧАСТЬ - График и таблица =====
        right_panel = tk.Frame(self.root)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # График
        self.figure, self.ax = plt.subplots(figsize=(10, 6))
        self.canvas = FigureCanvasTkAgg(self.figure, right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Подключаем события мыши
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        
        self.dragging_point = None
        
        # Таблица координат
        table_frame = tk.LabelFrame(right_panel, text="Координаты точек текущей кривой", font=('Arial', 10, 'bold'))
        table_frame.pack(fill=tk.X, pady=5)
        
        # Создаем таблицу
        columns = ("№", "X", "Y")
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=6)
        self.tree.heading("№", text="№")
        self.tree.heading("X", text="X")
        self.tree.heading("Y", text="Y")
        self.tree.column("№", width=50)
        self.tree.column("X", width=100)
        self.tree.column("Y", width=100)
        self.tree.pack(fill=tk.X, padx=5, pady=5)
        
    def create_plot(self):
        """Создание начального графика"""
        self.ax.clear()
        self.ax.set_xlim(0, self.x_max)
        self.ax.set_ylim(0, self.y_max)
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.grid(self.grid_enabled, alpha=0.3)
        self.canvas.draw()
        
    def create_curves(self):
        """Создание заданного количества кривых"""
        try:
            num = int(self.num_curves_var.get())
            if num < 1:
                messagebox.showerror("Ошибка", "Количество кривых должно быть больше 0")
                return
            
            self.curves = []
            colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "cyan"]
            
            for i in range(num):
                self.curves.append({
                    'points': [],
                    'color': colors[i % len(colors)],
                    'line_style': 'solid',
                    'marker': 'o',
                    'label': f'Кривая {i+1}',
                    'show_points': True
                })
            
            self.update_curves_list()
            self.update_plot()
            messagebox.showinfo("Успех", f"Создано {num} кривых")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное число")
    
    def update_curves_list(self):
        """Обновление списка кривых"""
        self.curves_listbox.delete(0, tk.END)
        for i, curve in enumerate(self.curves):
            self.curves_listbox.insert(tk.END, f"{i+1}. {curve['label']} ({len(curve['points'])} точек)")
    
    def on_curve_select(self, event):
        """Выбор кривой из списка"""
        selection = self.curves_listbox.curselection()
        if selection:
            self.current_curve_index = selection[0]
            curve = self.curves[self.current_curve_index]
            
            # Обновляем поля настроек
            self.curve_label_var.set(curve['label'])
            self.line_color_var.set(curve['color'])
            self.line_style_var.set(curve['line_style'])
            self.marker_var.set(curve['marker'])
            self.show_points_var.set(curve['show_points'])
            
            self.update_table()
    
    def update_curve_settings(self):
        """Применение настроек к текущей кривой"""
        if self.current_curve_index is None:
            messagebox.showwarning("Предупреждение", "Выберите кривую из списка")
            return
        
        curve = self.curves[self.current_curve_index]
        curve['label'] = self.curve_label_var.get()
        curve['color'] = self.line_color_var.get()
        curve['line_style'] = self.line_style_var.get()
        curve['marker'] = self.marker_var.get()
        curve['show_points'] = self.show_points_var.get()
        
        self.update_curves_list()
        self.update_plot()
    
    def apply_settings(self):
        """Применение общих настроек графика"""
        try:
            self.x_label = self.x_label_var.get()
            self.y_label = self.y_label_var.get()
            self.x_max = float(self.x_max_var.get())
            self.y_max = float(self.y_max_var.get())
            self.grid_step_x = float(self.grid_x_var.get())
            self.grid_step_y = float(self.grid_y_var.get())
            self.grid_enabled = self.grid_enabled_var.get()
            
            self.update_plot()
            messagebox.showinfo("Успех", "Настройки применены")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Проверьте корректность введенных значений")
    
    def change_mode(self):
        """Смена режима работы"""
        self.mode = self.mode_var.get()
    
    def clear_current_curve(self):
        """Очистка текущей кривой"""
        if self.current_curve_index is None:
            messagebox.showwarning("Предупреждение", "Выберите кривую")
            return
        
        curve = self.curves[self.current_curve_index]
        if len(curve['points']) == 0:
            messagebox.showinfo("Информация", "Кривая уже пуста")
            return
        
        if messagebox.askyesno("Подтверждение", 
                              f"Удалить все {len(curve['points'])} точек из кривой '{curve['label']}'?"):
            curve['points'] = []
            self.update_plot()
            self.update_table()
            self.update_curves_list()
            messagebox.showinfo("Успех", "Кривая очищена")
    
    def on_click(self, event):
        """Обработка клика по графику"""
        if event.inaxes != self.ax or self.current_curve_index is None:
            return
        
        x, y = event.xdata, event.ydata
        
        if self.mode == "add":
            # Добавление точки
            self.curves[self.current_curve_index]['points'].append((x, y))
            self.update_plot()
            self.update_table()
            self.update_curves_list()
            
        elif self.mode == "delete":
            # Удаление ближайшей точки
            curve = self.curves[self.current_curve_index]
            if curve['points']:
                # Находим ближайшую точку
                min_dist = float('inf')
                min_idx = -1
                for i, (px, py) in enumerate(curve['points']):
                    dist = ((px - x)**2 + (py - y)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
                
                if min_idx != -1 and min_dist < 0.5:  # Порог близости
                    curve['points'].pop(min_idx)
                    self.update_plot()
                    self.update_table()
                    self.update_curves_list()
        
        elif self.mode == "move":
            # Начало перетаскивания точки
            curve = self.curves[self.current_curve_index]
            if curve['points']:
                min_dist = float('inf')
                min_idx = -1
                for i, (px, py) in enumerate(curve['points']):
                    dist = ((px - x)**2 + (py - y)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = i
                
                if min_idx != -1 and min_dist < 0.5:
                    self.dragging_point = min_idx
    
    def on_motion(self, event):
        """Обработка движения мыши"""
        if self.mode == "move" and self.dragging_point is not None and event.inaxes == self.ax:
            curve = self.curves[self.current_curve_index]
            curve['points'][self.dragging_point] = (event.xdata, event.ydata)
            self.update_plot()
            self.update_table()
    
    def on_release(self, event):
        """Отпускание кнопки мыши"""
        self.dragging_point = None
    
    def smooth_curve(self):
        """Сглаживание текущей кривой"""
        if self.current_curve_index is None:
            messagebox.showwarning("Предупреждение", "Выберите кривую")
            return
        
        curve = self.curves[self.current_curve_index]
        if len(curve['points']) < 3:
            messagebox.showwarning("Предупреждение", "Для сглаживания нужно минимум 3 точки")
            return
        
        # Сортируем точки по X
        points = sorted(curve['points'], key=lambda p: p[0])
        x_data = [p[0] for p in points]
        y_data = [p[1] for p in points]
        
        # Создаем сглаженную кривую
        try:
            x_smooth = np.linspace(min(x_data), max(x_data), 100)
            spl = make_interp_spline(x_data, y_data, k=3)
            y_smooth = spl(x_smooth)
            
            # Заменяем точки на сглаженные
            curve['points'] = list(zip(x_smooth, y_smooth))
            self.update_plot()
            self.update_table()
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сгладить: {str(e)}")
    
    def build_from_formula(self):
        """Построение графика по формуле с возможностью последующего редактирования"""
        if self.current_curve_index is None:
            messagebox.showwarning("Предупреждение", "Выберите кривую")
            return
        
        formula = self.formula_var.get()
        try:
            num_points = int(self.formula_points_var.get())
            if num_points < 2:
                messagebox.showerror("Ошибка", "Количество точек должно быть больше 1")
                return
            
            x_vals = np.linspace(0, self.x_max, num_points)
            
            # Поддержка различных функций
            # Создаем безопасное окружение для eval
            safe_dict = {
                "x": x_vals,
                "np": np,
                "sin": np.sin,
                "cos": np.cos,
                "tan": np.tan,
                "exp": np.exp,
                "log": np.log,
                "log10": np.log10,
                "sqrt": np.sqrt,
                "abs": np.abs,
                "pi": np.pi,
                "e": np.e
            }
            
            y_vals = eval(formula, {"__builtins__": {}}, safe_dict)
            
            # Проверка на корректность результата
            if isinstance(y_vals, (int, float)):
                y_vals = np.full(num_points, y_vals)
            
            # Заменяем точки кривой на вычисленные
            curve = self.curves[self.current_curve_index]
            curve['points'] = list(zip(x_vals, y_vals))
            
            self.update_plot()
            self.update_table()
            self.update_curves_list()
            
            messagebox.showinfo("Успех", 
                f"График построен по формуле: y = {formula}\n"
                f"Создано {num_points} точек\n\n"
                f"Теперь вы можете:\n"
                f"• Добавить новые точки (режим 'Добавить точку')\n"
                f"• Удалить точки (режим 'Удалить точку')\n"
                f"• Переместить точки (режим 'Переместить точку')\n"
                f"• Сгладить кривую")
            
        except Exception as e:
            messagebox.showerror("Ошибка", 
                f"Некорректная формула: {str(e)}\n\n"
                f"Примеры формул:\n"
                f"• x**2 (парабола)\n"
                f"• sin(x) (синус)\n"
                f"• exp(x) (экспонента)\n"
                f"• x**3 - 2*x + 1\n"
                f"• sqrt(x)\n"
                f"• log(x + 1)")
    
    def save_graph(self, format_type):
        """Сохранение графика в файл"""
        # Диалог выбора файла
        filetypes = {
            'png': [("PNG изображение", "*.png")],
            'pdf': [("PDF документ", "*.pdf")],
            'svg': [("SVG векторная графика", "*.svg")]
        }
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=filetypes.get(format_type, [("Все файлы", "*.*")]),
            title="Сохранить график"
        )
        
        if filename:
            try:
                # Создаем копию текущего графика для сохранения
                fig_save = plt.figure(figsize=(12, 8))
                ax_save = fig_save.add_subplot(111)
                
                # Копируем настройки
                ax_save.set_xlim(0, self.x_max)
                ax_save.set_ylim(0, self.y_max)
                ax_save.set_xlabel(self.x_label, fontsize=14)
                ax_save.set_ylabel(self.y_label, fontsize=14)
                ax_save.grid(self.grid_enabled, alpha=0.3)
                ax_save.set_title("График", fontsize=16, fontweight='bold')
                
                # Рисуем все кривые
                for curve in self.curves:
                    if len(curve['points']) > 0:
                        points = sorted(curve['points'], key=lambda p: p[0])
                        x_data = [p[0] for p in points]
                        y_data = [p[1] for p in points]
                        
                        ax_save.plot(x_data, y_data, 
                                   color=curve['color'], 
                                   linestyle=curve['line_style'],
                                   marker=curve['marker'] if curve['show_points'] else '',
                                   markersize=8,
                                   linewidth=2,
                                   label=curve['label'])
                
                if self.curves:
                    ax_save.legend(fontsize=12)
                
                # Сохраняем с высоким качеством
                fig_save.savefig(filename, dpi=300, bbox_inches='tight')
                plt.close(fig_save)
                
                messagebox.showinfo("Успех", f"График сохранен:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить: {str(e)}")
    
    def print_graph(self):
        """Печать графика"""
        try:
            # Сохраняем во временный файл
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_filename = temp_file.name
            temp_file.close()
            
            # Создаем график для печати
            fig_print = plt.figure(figsize=(11, 8.5))  # Размер A4
            ax_print = fig_print.add_subplot(111)
            
            # Копируем настройки
            ax_print.set_xlim(0, self.x_max)
            ax_print.set_ylim(0, self.y_max)
            ax_print.set_xlabel(self.x_label, fontsize=14)
            ax_print.set_ylabel(self.y_label, fontsize=14)
            ax_print.grid(self.grid_enabled, alpha=0.3)
            ax_print.set_title("График", fontsize=16, fontweight='bold')
            
            # Рисуем все кривые
            for curve in self.curves:
                if len(curve['points']) > 0:
                    points = sorted(curve['points'], key=lambda p: p[0])
                    x_data = [p[0] for p in points]
                    y_data = [p[1] for p in points]
                    
                    ax_print.plot(x_data, y_data, 
                               color=curve['color'], 
                               linestyle=curve['line_style'],
                               marker=curve['marker'] if curve['show_points'] else '',
                               markersize=8,
                               linewidth=2,
                               label=curve['label'])
            
            if self.curves:
                ax_print.legend(fontsize=12)
            
            # Сохраняем
            fig_print.savefig(temp_filename, dpi=300, bbox_inches='tight')
            plt.close(fig_print)
            
            # Открываем файл для печати (зависит от ОС)
            if os.name == 'nt':  # Windows
                os.startfile(temp_filename, 'print')
            elif os.name == 'posix':  # Linux/Mac
                import subprocess
                if os.uname().sysname == 'Darwin':  # Mac
                    subprocess.call(['lpr', temp_filename])
                else:  # Linux
                    subprocess.call(['lp', temp_filename])
            
            messagebox.showinfo("Печать", "Документ отправлен на печать")
            
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось распечатать: {str(e)}\n\nВы можете сохранить график и распечатать вручную.")
    
    def update_plot(self):
        """Обновление графика"""
        self.ax.clear()
        self.ax.set_xlim(0, self.x_max)
        self.ax.set_ylim(0, self.y_max)
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.grid(self.grid_enabled, alpha=0.3)
        
        # Флаг - есть ли данные для легенды
        has_data = False
        
        # Рисуем все кривые
        for curve in self.curves:
            if len(curve['points']) > 0:
                has_data = True
                points = sorted(curve['points'], key=lambda p: p[0])
                x_data = [p[0] for p in points]
                y_data = [p[1] for p in points]
                
                # Рисуем линию
                self.ax.plot(x_data, y_data, 
                           color=curve['color'], 
                           linestyle=curve['line_style'],
                           marker=curve['marker'] if curve['show_points'] else '',
                           markersize=8,
                           label=curve['label'])
        
        # Показываем легенду только если есть данные
        if has_data:
            self.ax.legend()
        
        self.canvas.draw()
    
    def update_table(self):
        """Обновление таблицы координат"""
        self.tree.delete(*self.tree.get_children())
        
        if self.current_curve_index is not None:
            curve = self.curves[self.current_curve_index]
            for i, (x, y) in enumerate(curve['points'], 1):
                self.tree.insert("", tk.END, values=(i, f"{x:.2f}", f"{y:.2f}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = GraphBuilder(root)
    root.mainloop()
