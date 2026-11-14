# R&T 智能马桶集成 (C80Lite)

Home Assistant 自定义集成，用于 **R&T（瑞尔特）C80Lite** 智能马桶的本地蓝牙（BLE）控制与状态读取。
支持 Home Assistant **2026.5 及以上**，完全使用 Home Assistant 内置的 `bluetooth` 集成（`habluetooth` + `bleak-retry-connector`），支持自动发现。

> 本集成由官方微信小程序 **「R&T智控」**（appid `wxd88d18786f43971e`）逆向分析得到，未使用任何云端接口，纯本地 BLE。

---

## 一、支持的功能

设备通过一个 **透传 BLE-UART 模块** 通信：

| 项目 | UUID |
| --- | --- |
| 数据服务 | `0000FFE0-0000-1000-8000-00805F9B34FB` |
| 数据特征（读写+通知） | `0000FFE1-0000-1000-8000-00805F9B34FB` |
| UID 服务（部分固件） | `0000FEE7-…` / `FEC7`(写) / `FEC8`(通知) |

广播名称包含 **`R&T`**，扫描按 `FFE0` 服务过滤。

### 实体
- **开关**：离座冲水、自动除臭、夜灯、智能夜灯、等离子杀菌、节能、自动翻盖、着座自动出泡、预湿润、静音模式、语音控制、男士小便自动冲、脚感冲水、酒店模式、久坐提醒、自动关盖、四季温感。
- **按钮**：臀洗、妇洗、暖风、童洗、儿童模式、大冲、小冲、静音冲、增强冲、停止、开盖/全开/全关、喷嘴清洁、手动除臭、出泡、AI 自清洁、一键自清洁、脉冲/移动/冷热清洗、移动暖风、各类关爱清洗、抽液/停止抽液。
- **选择**：水温、座温、风温（档位 28–38 ℃）。
- **数值**：水压强度、喷嘴位置、风速。
- **传感器**：设备状态、冲水状态、健康功能、设定水温/座温/风温。
- **二进制传感器**：着座。

---

## 二、协议摘要

帧格式（大端）：

```
55 AA  <len>  <deviceType>  <cmdType>  <paramLen>  <params...>  <devModel hi lo>  <checksum>
```

- `len` = 其后到校验和为止的字节数（含校验和）。
- `checksum` = `sum(len 之后除校验和外的所有字节) & 0xFF`。
- 命令参数固定为 `[0xA1, code, b0..b7]`，`b0..b7` 是 8 字节位域数组，按 `(position, bit-range)` 写入（bit7 为字节最高位）。
- 命令类型 `cmdType`：`2` 控制、`4` 版本查询、`13` 功能查询(featSel)。
- 设备上报 `cmdType`：`3` 状态更新(updateStatus)、`130` 下发(distribute)、`141` 功能选择、`132` 版本、`139` OTA。
- 收到状态更新(3) 需回 `cmdType=131` 的 ACK（回显参数）。

连接握手：`connect(空命令) → featSel → versionQuery`。

以上位域 / 指令码取自小程序内置的 `MCUFunctionInfo`，完整表格见 [`protocol_data.py`](protocol_data.py)（`FUNCTION_PARAM_CODE_LIST` / `FUNCTION_OPERATION_LIST`）。

---

## 三、安装

1. 将本目录 `rt_toilet` 复制到 HA 配置目录的 `custom_components/` 下。
2. 重启 Home Assistant。
3. 马桶开机并在蓝牙范围内，HA 会自动发现（名称含 `R&T`），或在「设置 → 设备与服务 → 添加集成 → R&T Smart Toilet」中手动选择设备。
4. 需要可用的蓝牙适配器；建议使用支持主动扫描的本地适配器或 ESPHome Bluetooth Proxy。

---

## 四、已知限制 / 说明

- 温度档位按 `28 + 2 × 档位` 换算，档位 0–5（28–38 ℃）；不同固件实际档位数可能不同，超出范围的值可能被设备忽略。
- 设备状态主要依赖其主动上报（`updateStatus`）。集成在连接及每 20 秒发送握手心跳，保证链路与状态刷新。
- 部分型号（含 C80Lite）的固件可能只暴露 `FFE0/FFE1` 或 `FEE7/FEC7/FEC8` 之一，集成会自动尝试。
- 首次连接若设备正在被手机小程序占用，请先在小程序中断开连接。
- 自动发现依赖设备在广播中包含 `FFE0` 服务 UUID；若个别固件不广播，可用手动添加。

---

## 五、目录结构

```
rt_toilet/
├── __init__.py         # 入口，加载协调器与平台
├── manifest.json       # 集成清单（bluetooth 依赖 + 发现匹配）
├── config_flow.py      # 自动发现 / 手动添加
├── coordinator.py      # BLE 连接、收发、重连、心跳
├── protocol.py         # 帧组装/解析、位域编解码
├── protocol_data.py    # 逆向得到的指令码/状态位域表（自动生成）
├── const.py            # 常量与实体定义
├── entity.py           # 实体基类
├── switch.py / button.py / select.py / number.py / sensor.py / binary_sensor.py
├── brand/                 # 品牌图标（取自官方小程序「R&T智控」图标）
├── strings.json / translations/
└── hacs.json
```

> 免责声明：本项目为个人逆向研究，与 R&T / 瑞尔特 官方无关。使用风险自负。
