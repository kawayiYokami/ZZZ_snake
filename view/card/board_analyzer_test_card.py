import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QWidget,
    QLabel,
    QFileDialog,
    QVBoxLayout,
    QFrame,
    QHBoxLayout,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from qfluentwidgets import (
    TitleLabel,
    TextEdit,
    PrimaryPushButton,
    SwitchButton,
    LineEdit,
    FluentIcon,
)
from log.log import SnakeLogger
from model.snake_board import Board
from analyzer.board.board_analyzer import BoardAnalyzer
from drawer.map_drawer import MapDrawer
from analyzer.path.path_finder import PathFinder
from PyQt5.QtWidgets import QSizePolicy


class ImageCard(QFrame):
    def __init__(self, width=500, height=500, parent=None):
        super().__init__(parent)
        self.setObjectName("ImageCard")
        self.setStyleSheet(
            """
            QFrame#ImageCard {
                border: 1px solid #cccccc;
                border-radius: 12px;
                background-color: transparent;
            }
            QLabel {
                border: none;
                background-color: transparent;
            }
        """
        )
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.label)

    def setPixmap(self, pixmap):
        self.label.setPixmap(pixmap)

    def clear(self):
        self.label.clear()


class BoardAnalyzerTestCard(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("subInterface_board_analyzer")
        self.setWindowTitle("棋盘分析测试")
        self.resize(1000, 800)  # 调整窗口大小

        # 主布局改为水平布局
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # 左侧图像区域
        left_layout = QVBoxLayout()
        left_layout.setSpacing(20)
        
        self.title = QLabel("棋盘识别与路径测试")
        self.title.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.title)

        self.image_card = ImageCard()
        left_layout.addWidget(self.image_card)

        # 右侧日志区域
        right_layout = QVBoxLayout()
        right_layout.setSpacing(20)

        # 日志标签
        log_label = QLabel("分析日志")
        log_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(log_label)

        # 日志文本框
        self.info_label = TextEdit()
        self.info_label.setReadOnly(True)
        self.info_label.setMinimumHeight(400)  # 增加高度
        right_layout.addWidget(self.info_label)

        # 将左右布局添加到主布局
        main_layout.addLayout(left_layout, stretch=2)  # 图像区域占2份
        main_layout.addLayout(right_layout, stretch=1)  # 日志区域占1份

        # 按钮布局保持不变
        button_layout = QHBoxLayout()
        self.open_button = PrimaryPushButton("打开图像")
        self.open_button.clicked.connect(self.open_image)

        self.direction_button = PrimaryPushButton("切换方向: 无")
        self.direction_button.clicked.connect(self.cycle_direction)
        self.directions = ["up", "down", "left", "right"]
        self.current_direction_index = -1
        self.current_direction = None

        self.detect_eye_button = PrimaryPushButton("检测蛇眼")
        self.detect_eye_button.clicked.connect(self.detect_snake_eye_show)

        self.path_finding_switch = SwitchButton("开启寻路")
        self.path_finding_switch.setChecked(True)

        self.filter_button = PrimaryPushButton("过滤区域")
        self.filter_button.setIcon(FluentIcon.FILTER)
        self.filter_button.clicked.connect(self.filter_hsv_mask)
        self.h_range_input = LineEdit()
        self.h_range_input.setPlaceholderText("H: 5")
        self.h_range_input.setText("5")
        self.s_range_input = LineEdit()
        self.s_range_input.setPlaceholderText("S: 50")
        self.s_range_input.setText("50")
        self.v_range_input = LineEdit()
        self.v_range_input.setPlaceholderText("V: 50")
        self.v_range_input.setText("50")

        hsv_layout = QHBoxLayout()
        hsv_layout.addWidget(self.filter_button)
        hsv_layout.addWidget(self.h_range_input)
        hsv_layout.addWidget(self.s_range_input)
        hsv_layout.addWidget(self.v_range_input)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.direction_button)
        button_layout.addWidget(self.detect_eye_button)

        # 将按钮布局添加到左侧布局底部
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.path_finding_switch, alignment=Qt.AlignCenter)
        left_layout.addLayout(hsv_layout)

        self.logger = SnakeLogger(self.info_label)
        self.analyzer = BoardAnalyzer(self.logger)
        self.current_pixmap = None
        self.current_hsv = None
        self.zoom_factor = 1.0
        self.current_board = None

    def cycle_direction(self):
        self.current_direction_index = (self.current_direction_index + 1) % len(
            self.directions
        )
        self.current_direction = self.directions[self.current_direction_index]
        self.direction_button.setText(f"切换方向: {self.current_direction}")
        if self.current_hsv is not None:
            self._analyze_and_draw(self.current_hsv)

    def detect_snake_eye_show(self):
        """
        蛇眼检测并绘制
        """
        if self.current_hsv is None:
            self.logger.warning("没有图像数据")
            return

        eyes = self.analyzer.find_snake_eye()
        self.logger.info(f"检测到蛇眼数量: {len(eyes)}")
        for pt in eyes:
            self.logger.info(f"蛇眼坐标: {pt}")

        # 一定要用当前HSV重新生成的BGR做绘制，避免覆盖
        hsv_img = self.current_hsv
        bgr_img = cv2.cvtColor(hsv_img, cv2.COLOR_HSV2BGR).copy()

        for cx, cy in eyes:
            # 绘制绿色中心点
            cv2.circle(bgr_img, (int(cx), int(cy)), 4, (0, 255, 0), -1)
            # 外圈红色圆
            cv2.circle(bgr_img, (int(cx), int(cy)), 10, (0, 0, 255), 2)

        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        h, w = rgb_img.shape[:2]
        bytes_per_line = 3 * w
        qimg = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888)

        self.current_pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = self.current_pixmap.scaled(
            self.image_card.label.width(),
            self.image_card.label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_card.setPixmap(scaled_pixmap)

    def wheelEvent(self, event):
        if self.current_pixmap:
            delta = event.angleDelta().y()
            self.zoom_factor *= 1.1 if delta > 0 else 0.9
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
            scaled_size = self.current_pixmap.size() * self.zoom_factor
            scaled_pixmap = self.current_pixmap.scaled(
                scaled_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_card.setPixmap(scaled_pixmap)

    def open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开图像", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not file_path:
            return
        import time

        read_start = time.time()
        image = cv2.imread(file_path)
        read_end = time.time()

        h0, w0 = image.shape[:2]
        if abs(w0 - 949) <= 5 and abs(h0 - 825) <= 5:
            resized = False
        else:
            resized = True

        resize_start = time.time()
        if resized:
            image = cv2.resize(image, (1920, 1080))
        resize_end = time.time()

        crop_start = time.time()
        if resized:
            image = image[203:1028, 485:1434]
        crop_end = time.time()

        hsv_start = time.time()
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        hsv_end = time.time()

        self.current_hsv = hsv
        self._analyze_and_draw(hsv)

    def _analyze_and_draw(self, hsv):
        import time

        board = Board(rows=25, cols=29, image=hsv, image_format="HSV")

        analyze_start = time.time()
        self.logger.debug(f"当前方向是: {self.current_direction}")
        board = self.analyzer.analyze_board(
            board, self.current_hsv, "HSV", self.current_direction
        )
        analyze_end = time.time()

        path = None
        path_time = 0
        if self.path_finding_switch.isChecked() and self.analyzer.is_running:
            pf = PathFinder(board.rows, board.cols, self.logger)
            path_start = time.time()
            path = pf.find_path_in_order(board)
            path_end = time.time()
            path_time = path_end - path_start

        drawer = MapDrawer(self.logger)
        draw_start = time.time()
        drawn_image = drawer.draw_map(board, path)
        draw_end = time.time()

        h_img, w_img = drawn_image.shape[:2]
        bytes_per_line = 3 * w_img
        rgb_image = cv2.cvtColor(drawn_image, cv2.COLOR_BGR2RGB)
        q_img = QImage(
            rgb_image.data, w_img, h_img, bytes_per_line, QImage.Format_RGB888
        )
        self.current_pixmap = QPixmap.fromImage(q_img)

        width_ratio = self.image_card.label.width() / self.current_pixmap.width()
        height_ratio = self.image_card.label.height() / self.current_pixmap.height()
        self.zoom_factor = min(width_ratio, height_ratio)

        scaled_pixmap = self.current_pixmap.scaled(
            self.image_card.label.width(),
            self.image_card.label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_card.setPixmap(scaled_pixmap)

        info = f"方向: {self.current_direction}\n"
        info += f"分析: {(analyze_end - analyze_start)*1000:.2f}ms\n"
        if self.path_finding_switch.isChecked():
            info += f"寻路: {path_time*1000:.2f}ms\n"
            info += f"结果: {'成功' if path else '未找到'}\n"
        info += f"绘制: {(draw_end - draw_start)*1000:.2f}ms\n"
        info += f"特殊格子: {len(self.analyzer.special_cells)}\n"
        info += f"游戏状态: {'运行中' if self.analyzer.is_running else '已停止'}"
        self.info_label.setText(info)

        self.current_board = board

        for row in board.cells:
            for cell in row:
                if cell:
                    cell.set_image(hsv)

    def filter_hsv_mask(self):
        if self.current_hsv is None:
            self.logger.warning("没有图像数据")
            return
        try:
            h_tol = int(self.h_range_input.text())
            s_tol = int(self.s_range_input.text())
            v_tol = int(self.v_range_input.text())
        except ValueError:
            self.logger.error("容差输入有误")
            return

        target_h, target_s, target_v = self.analyzer.grid_colors_hsv["own_head"]
        target_h, target_s, target_v = [0, 0, 255]
        lower = np.array(
            [
                max(0, target_h - h_tol),
                max(0, target_s - s_tol),
                max(0, target_v - v_tol),
            ]
        )
        upper = np.array(
            [
                min(179, target_h + h_tol),
                min(255, target_s + s_tol),
                min(255, target_v + v_tol),
            ]
        )

        mask = cv2.inRange(self.current_hsv, lower, upper)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.logger.info(f"找到 {len(contours)} 个连通区域")

        color_img = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
        color_img[mask == 0] = (128, 128, 128)

        if contours:
            max_contour = max(contours, key=cv2.contourArea)
            points = max_contour.reshape(-1, 2)

            up_point = tuple(points[np.argmin(points[:, 1])])
            down_point = tuple(points[np.argmax(points[:, 1])])
            left_point = tuple(points[np.argmin(points[:, 0])])
            right_point = tuple(points[np.argmax(points[:, 0])])

            self.logger.info(f"最上点 (up): {up_point}")
            self.logger.info(f"最下点 (down): {down_point}")
            self.logger.info(f"最左点 (left): {left_point}")
            self.logger.info(f"最右点 (right): {right_point}")

            edge_point = None
            dir = self.current_direction
            if dir == "up":
                edge_point = up_point
            elif dir == "down":
                edge_point = down_point
            elif dir == "left":
                edge_point = left_point
            elif dir == "right":
                edge_point = right_point

            if edge_point is not None:
                color = (0, 0, 255)
                radius = 15
                thickness = 15
                cv2.line(
                    color_img,
                    (edge_point[0] - radius, edge_point[1]),
                    (edge_point[0] + radius, edge_point[1]),
                    color,
                    thickness,
                )
                cv2.line(
                    color_img,
                    (edge_point[0], edge_point[1] - radius),
                    (edge_point[0], edge_point[1] + radius),
                    color,
                    thickness,
                )
                self.logger.info(f"{dir}方向选中的边缘点坐标: {edge_point}")

        h_img, w_img = color_img.shape[:2]
        bytes_per_line = 3 * w_img
        rgb_image = cv2.cvtColor(color_img, cv2.COLOR_BGR2RGB)
        q_img = QImage(
            rgb_image.data, w_img, h_img, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(
            self.image_card.label.width(),
            self.image_card.label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.current_pixmap = pixmap
        self.zoom_factor = 1.0
        self.image_card.setPixmap(scaled_pixmap)

    def mousePressEvent(self, event):
        if not (self.current_board and self.current_pixmap):
            return

        label_point = self.image_card.label.mapFromGlobal(event.globalPos())
        x = label_point.x()
        y = label_point.y()

        label_width = self.image_card.label.width()
        label_height = self.image_card.label.height()

        pix = self.image_card.label.pixmap()
        if pix is None:
            return
        pix_w = pix.width()
        pix_h = pix.height()

        x_offset = (label_width - pix_w) / 2
        y_offset = (label_height - pix_h) / 2

        x_image = x - x_offset
        y_image = y - y_offset

        if x_image < 0 or y_image < 0 or x_image > pix_w or y_image > pix_h:
            return

        col_width = pix_w / self.current_board.cols
        row_height = pix_h / self.current_board.rows
        col = int(x_image / col_width)
        row = int(y_image / row_height)

        if 0 <= row < self.current_board.rows and 0 <= col < self.current_board.cols:
            cell = self.current_board.cells[row][col]
            if cell:
                info = f"格子: 行{row+1} 列{col+1}\n类型: {cell.cell_type}\n中心: {cell.center}\n"
                if hasattr(cell, "center_color") and cell.center_color is not None:
                    info += f"HSV中心色: {cell.center_color}\n"
                if hasattr(cell, "color_dict") and cell.color_dict:
                    info += "颜色统计:\n"
                    sorted_colors = sorted(
                        cell.color_dict.items(), key=lambda x: x[1], reverse=True
                    )
                    for k, v in sorted_colors:
                        info += f"  {k}: {v}\n"
                if hasattr(cell, "bounds"):
                    info += f"边界: {cell.bounds}\n"

                # 新增: 输出该像素点击的HSV值
                if self.current_hsv is not None:
                    # 计算在hsv图像中的物理像素坐标
                    h_hsv, w_hsv = self.current_hsv.shape[:2]
                    x_hsv = int(x_image / pix_w * w_hsv)
                    y_hsv = int(y_image / pix_h * h_hsv)
                    if 0 <= y_hsv < h_hsv and 0 <= x_hsv < w_hsv:
                        hsv_val = self.current_hsv[y_hsv, x_hsv]
                        info += f"点击像素HSV值: ({hsv_val[0]}, {hsv_val[1]}, {hsv_val[2]})\n"

                self.info_label.setText(info)
                self.info_label.verticalScrollBar().setValue(
                    self.info_label.verticalScrollBar().maximum()
                )


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    w = BoardAnalyzerTestCard()
    w.show()
    sys.exit(app.exec_())
