"""Constants and entity definitions for the R&T C80Lite smart toilet."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "rt_toilet"
NAME = "R&T 智能马桶"
MANUFACTURER = "R&T (瑞尔特)"
MODEL = "C80Lite"

CONF_ADDRESS = "address"

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

# How often to make sure the BLE link is still up (seconds).
CONNECT_RETRY_SECONDS = 15
KEEPALIVE_SECONDS = 20

# --- switch entities -----------------------------------------------------
# (mark, name, icon).  ``mark`` is a key of FUNCTION_OPERATION_LIST and, for
# the status side, of FUNCTION_PARAM_CODE_LIST.
SWITCHES: list[tuple[str, str, str]] = [
    ("autoFlush", "离座冲水", "mdi:toilet"),
    ("autoDeodorize", "自动除臭", "mdi:air-filter"),
    ("nightLight", "夜灯", "mdi:lightbulb-night"),
    ("smartNightLight", "智能夜灯", "mdi:lightbulb-auto"),
    ("plasmaSterilize", "等离子杀菌", "mdi:shield-star"),
    ("powerSaving", "节能", "mdi:leaf"),
    ("autoFlipCover", "自动翻盖", "mdi:toilet"),
    ("foamShield", "着座自动出泡", "mdi:soap"),
    ("autoPreheatSwitch", "预湿润", "mdi:water"),
    ("mute", "静音模式", "mdi:volume-off"),
    ("voiceSwitch", "语音控制", "mdi:microphone"),
    ("urineSwitch", "男士小便自动冲", "mdi:human-male"),
    ("footWashSwitch", "脚感冲水", "mdi:foot-print"),
    ("hotelModeSwitch", "酒店模式", "mdi:office-building"),
    ("sitRemindSwitch", "久坐提醒", "mdi:timer-alert"),
    ("autoCloseCover", "自动关盖", "mdi:toilet"),
    ("fourSeasonsTemperatureSwitch", "四季温感", "mdi:thermometer"),
]

# --- button entities (momentary actions) ---------------------------------
BUTTONS: list[tuple[str, str, str]] = [
    ("hipWash", "臀洗", "mdi:toilet"),
    ("femaleWash", "妇洗", "mdi:toilet"),
    ("dry", "暖风", "mdi:hair-dryer"),
    ("kidWash", "童洗", "mdi:human-child"),
    ("kidMode", "儿童模式", "mdi:human-child"),
    ("bigFlush", "大冲", "mdi:water-pump"),
    ("smallFlush", "小冲", "mdi:water-pump"),
    ("muteFlush", "静音冲", "mdi:water-pump"),
    ("enhancedFlush", "增强冲", "mdi:water-pump"),
    ("stop", "停止", "mdi:stop"),
    ("openUpperCover", "开盖", "mdi:arrow-up-bold"),
    ("openUpperCoverSeat", "全开", "mdi:arrow-up-bold-box-outline"),
    ("closeUpperCoverSeat", "全关", "mdi:arrow-down-bold-box-outline"),
    ("sprayClean", "喷嘴清洁", "mdi:spray"),
    ("manualDeodorize", "手动除臭", "mdi:air-filter"),
    ("outBubble", "出泡", "mdi:soap"),
    ("autoClean", "AI 自清洁", "mdi:robot-vacuum"),
    ("manualClean", "一键自清洁", "mdi:auto-fix"),
    ("pulseMassage", "脉冲清洗", "mdi:sine-wave"),
    ("moveMassage", "移动清洗", "mdi:swap-horizontal"),
    ("coldHotMassage", "冷热清洗", "mdi:thermometer-plus"),
    ("moveDry", "移动暖风", "mdi:hair-dryer"),
    ("healthy_female_care", "关爱妇洗", "mdi:flower"),
    ("healthy_piles", "舒缓痔洗", "mdi:medical-bag"),
    ("healthy_defecate", "强净助便", "mdi:medical-bag"),
    ("healthy_female_gentle", "柔净妇洗", "mdi:flower"),
    ("healthy_rump", "洁净臀洗", "mdi:toilet"),
    ("cleanFemaleWash", "洁净妇洗", "mdi:flower"),
    ("defecateWash", "助便清洗", "mdi:medical-bag"),
    ("extractLiquid", "抽液", "mdi:water-minus"),
    ("stopExtractLiquid", "停止抽液", "mdi:water-off"),
]

# --- temperature selects -------------------------------------------------
# The device stores a level index; displayed value = min + step * index.
TEMPERATURE_MIN = 28
TEMPERATURE_STEP = 2
TEMPERATURE_LEVELS = 6  # indices 0..5  ->  28..38 °C

SELECTS: list[tuple[str, str, str]] = [
    ("waterTemperature", "水温", "mdi:thermometer-water"),
    ("seatTemperature", "座温", "mdi:thermometer"),
    ("windTemperature", "风温", "mdi:weather-windy"),
]

# --- numeric controls ----------------------------------------------------
# (mark, name, icon, min, max, step)
NUMBERS: list[tuple[str, str, str, float, float, float]] = [
    ("waterPressure", "水压强度", "mdi:water-percent", 0, 5, 1),
    ("sprayPosition", "喷嘴位置", "mdi:arrow-expand-horizontal", 0, 5, 1),
    ("windSpeed", "风速", "mdi:weather-windy", 0, 3, 1),
]

# --- sensors -------------------------------------------------------------
# (mark, name, icon, kind)  kind: "text" | "temp" | "raw" | "rssi"
SENSORS: list[tuple[str, str, str, str]] = [
    ("rssi", "蓝牙信号强度", "mdi:signal", "rssi"),
    ("flipCoverStatus", "盖板状态码", "mdi:toilet", "raw"),
    ("deviceStatus", "设备状态", "mdi:toilet", "text"),
    ("flushStatus", "冲水状态", "mdi:water", "text"),
    ("healthyVitalityPopup", "健康功能", "mdi:heart-pulse", "text"),
    ("waterTemperature", "设定水温", "mdi:thermometer-water", "temp"),
    ("seatTemperature", "设定座温", "mdi:thermometer", "temp"),
    ("windTemperature", "设定风温", "mdi:weather-windy", "temp"),
]

# (mark, name, icon) — binary sensor is on when raw value == 1
BINARY_SENSORS: list[tuple[str, str, str]] = [
    ("seatStatus", "着座", "mdi:seat"),
]
