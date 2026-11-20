APP_STYLESHEET = r'''
QWidget { background: #0c0c10; color: #eee9ed; font-family: "Segoe UI"; font-size: 13px; }
QFrame#sidebar { background: #101014; border-right: 1px solid #2c1c23; }
QLabel { background: transparent; }
QLabel#brand { color: #ff354f; font-size: 27px; font-weight: 700; letter-spacing: 4px; }
QLabel#brandSub { color: #817078; font-size: 10px; }
QLabel#pageTitle { color: #fff4f6; font-size: 27px; font-weight: 600; }
QLabel#pageSubtitle { color: #978b94; font-size: 12px; }
QLabel#sectionTitle { color: #e8dfe5; font-size: 15px; font-weight: 600; }
QLabel#commandLabel { color: #ae7a87; font-size: 10px; letter-spacing: 2px; }
QLabel#commandText { color: #ff5268; font-size: 21px; font-weight: 600; }
QLabel#commandQuote { color: #a79aa3; }
QFrame#commandPanel, QFrame#logPanel, QFrame#statusCard { background: #141318; border: 1px solid #30232b; border-radius: 12px; }
QPushButton { background: #20171e; color: #d7c7d0; border: 1px solid #49303a; border-radius: 7px; padding: 9px 14px; }
QPushButton:hover { background: #35212b; border-color: #bd3047; color: #fff3f7; }
QPushButton:pressed { background: #5c2232; }
QPushButton:disabled { color: #70646c; background: #171419; border-color: #292129; }
QPushButton#navButton { background: transparent; border: 1px solid transparent; text-align: left; padding: 13px 14px; color: #95858e; }
QPushButton#navButton[active="true"] { background: #32131e; border: 1px solid #8f263a; color: #ff5a70; }
QPushButton#primaryButton { background: #c72440; border-color: #ef3a55; color: white; padding: 12px 18px; font-weight: 600; }
QPushButton#primaryButton:hover { background: #e12b49; }
QPushButton#primaryButton[running="true"] { background: #421b28; }
QPushButton#clearButton { background: transparent; border: none; padding: 3px; color: #d74b63; font-size: 11px; }
QListWidget { background: #121116; border: 1px solid #30232b; border-radius: 8px; outline: none; }
QListWidget::item { padding: 13px 10px; border-bottom: 1px solid #251c23; }
QListWidget::item:selected { background: #3b1b29; color: #ffabb8; }
QListWidget#eventList { border: none; background: transparent; color: #a99aa4; font-size: 12px; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox { background: #17131a; border: 1px solid #4a303c; border-radius: 6px; padding: 8px; selection-background-color: #a82944; }
QComboBox QAbstractItemView { background: #1e1720; selection-background-color: #5b2539; }
QCheckBox { spacing: 10px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #694052; border-radius: 4px; background: #1b131b; }
QCheckBox::indicator:checked { background: #dc2c4d; border-color: #ff657e; }
QSlider::groove:horizontal { height: 4px; background: #472332; border-radius: 2px; }
QSlider::handle:horizontal { background: #ff3a5a; width: 16px; margin: -6px 0; border-radius: 8px; }
QProgressBar { background: #2b1520; border: none; border-radius: 3px; }
QProgressBar::chunk { background: #ff3757; border-radius: 3px; }
QStatusBar { background: #101014; color: #8d707d; border-top: 1px solid #2f1c26; font-size: 11px; }
QScrollBar:vertical { background: #131016; width: 8px; }
QScrollBar::handle:vertical { background: #613246; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #2b1823; color: #ffdfeb; border: 1px solid #8f3550; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: #19131b; color: #a6939f; border: 1px solid #3f2835; padding: 9px 14px; }
QTabBar::tab:selected { color: #ff7b94; border-bottom: 2px solid #ee3656; background: #2c1521; }
'''
