# 科沃斯 T90 Pro 中国区地图补丁

这是一个面向 Home Assistant 的 HACS 自定义集成，用于修复科沃斯
T90 Pro 中国区机型在官方 **Ecovacs** 集成中无法识别设备能力、无法读取地图，
或地图缺少房间信息的问题。

当前已在以下环境实机验证：

- Home Assistant `2026.7.2`
- 官方 Ecovacs 集成
- `deebot-client 18.4.0`
- 中国区 T90 Pro 硬件类 `guaexd`

本项目不保存科沃斯账号和密码，也不替代官方 Ecovacs 集成。登录、设备控制和
云端通信仍由 Home Assistant 官方 Ecovacs 集成负责。

## 功能

- 为 `guaexd` 注册兼容的 T90 Pro 设备能力
- 支持中国区固件使用的 V2 地图协议
- 获取当前地图、房间、机器人位置、充电座位置和清扫轨迹
- 在 SVG 地图中加入房间名称和可选择的房间区域
- 自带中文地图卡片，支持缩放、弹窗大图、房间选择和分区清扫
- HACS 安装后自动加载地图卡片，不需要复制 JS 文件或添加 Lovelace 资源
- 检测到上游已经原生支持时，自动优先使用官方实现

## 安装前提

请先在 Home Assistant 中配置好官方 **Ecovacs** 集成，并确认 T90 Pro 已经登录到
同一个科沃斯账号。

## HACS 安装（推荐）

点击下面的按钮可在 Home Assistant 中打开 HACS 自定义仓库页面：

[![在 HACS 中打开](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lifujie25&repository=ha-ecovacs-t90-pro&category=integration)

也可以手工操作：

1. 打开 **HACS → 右上角菜单 → 自定义存储库**。
2. 仓库填写 `https://github.com/lifujie25/ha-ecovacs-t90-pro`。
3. 类别选择 **集成**，然后添加并下载。
4. 重启 Home Assistant。
5. 打开 **设置 → 设备与服务 → 添加集成**。
6. 搜索并添加 **科沃斯 T90 Pro 中国区地图补丁**。

添加时不需要再次输入科沃斯账号。补丁会自动安装设备能力并重新加载现有的
官方 Ecovacs 集成。

## 添加地图卡片

安装补丁并重启后：

1. 打开任意仪表盘，进入编辑模式。
2. 点击 **添加卡片**。
3. 搜索 **科沃斯 T90 地图**。
4. 在图形化配置中选择地图图像实体和扫地机器人实体。
5. 保存。

地图图像实体通常类似：

```text
image.ke_ting_t90_pro_map
```

扫地机器人实体通常类似：

```text
vacuum.t90_pro
```

也可以使用 YAML：

```yaml
type: custom:ecovacs-t90-map-card
title: T90 Pro 地图
image_entity: image.ke_ting_t90_pro_map
vacuum_entity: vacuum.t90_pro
refresh_interval: 10
```

不需要再把 `ecovacs-t90-map-card.js` 复制到 `/config/www`，也不需要在仪表盘资源
中添加 `/local/ecovacs-t90-map-card.js`。

## 从旧版手工安装迁移

如果之前已经手工复制过 `ecovacs_t90_patch`：

1. 先用 HACS 下载本仓库，覆盖同名集成目录。
2. 重启 Home Assistant。
3. 确认补丁集成和地图正常。
4. 删除仪表盘资源中的旧 `/local/ecovacs-t90-map-card.js` 条目。
5. `/config/www/ecovacs-t90-map-card.js` 旧文件可以删除。

已有仪表盘卡片配置不需要修改。

## 工作原理

中国区 T90 Pro 使用的硬件类为 `guaexd`。补丁以现有 T90 Pro 能力配置为基础，
加入当前固件使用的 `getInfo`、`getMapInfo_V2`、`getMapSet_V2`、`getPos_V2`
和 `getMapTrace` 命令，并避免调用该机型不支持的旧版 `getMajorMap` 命令。

如果未来 `deebot-client` 已经为 `guaexd` 提供完整地图能力，本补丁会停止覆盖，
直接使用上游官方配置。

## 常见问题

### 添加补丁后仍然没有地图实体

先确认官方 Ecovacs 集成中已经出现 T90 Pro，并尝试重新加载官方 Ecovacs 集成。
如果设备仍不可用，请在问题反馈中附上 Home Assistant 版本、补丁版本和经过脱敏的
相关日志。

### 地图卡片没有出现在卡片列表

确认已经重启 Home Assistant，并已在 **设置 → 设备与服务** 中添加本补丁集成。
浏览器强制刷新一次后再进入卡片选择器。

### 是否支持其他科沃斯型号

当前只针对中国区 T90 Pro 硬件类 `guaexd`。其他型号可能使用不同协议，请勿直接
套用；可以提交问题并附上脱敏后的型号和硬件类信息。

## 卸载

1. 在 **设置 → 设备与服务** 中删除本补丁集成。
2. 在 HACS 中卸载本仓库。
3. 重启 Home Assistant。

卸载不会删除官方 Ecovacs 集成，也不会删除科沃斯账号或设备。

## 问题反馈

请到 [GitHub Issues](https://github.com/lifujie25/ha-ecovacs-t90-pro/issues)
反馈。请勿上传科沃斯账号、密码、访问令牌、家庭地址或完整未脱敏日志。

## 免责声明

本项目为社区兼容补丁，与科沃斯及 Home Assistant 官方无隶属关系。地图和分区
清扫属于设备控制功能，请先在有人看护的环境中验证。
