---
version: alpha
name: Pan
description: "像整理一张清爽的工作台：文件本身是主角，路径、容量和操作始终可预期"
colors:
  primary: "#176B5B"
  primary-hover: "#12584B"
  primary-active: "#0D463C"
  primary-soft: "#E8F3F0"
  background: "#F4F6F3"
  surface: "#FFFFFF"
  surface-muted: "#F8FAF8"
  text: "#1C2824"
  text-secondary: "#52615C"
  text-muted: "#78857F"
  border: "#DDE4E0"
  success: "#16835D"
  warning: "#B66A16"
  danger: "#C84747"
typography:
  page-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.35
  section-title:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.45
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
  body-sm:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  button:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: "4px"
  md: "8px"
  lg: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  section: "48px"
components:
  primary-button:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
  primary-button-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.surface}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
  primary-button-active:
    backgroundColor: "{colors.primary-active}"
    textColor: "{colors.surface}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
  text-input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    borderColor: "{colors.border}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
---

# Pan Design

## Overview

- 具体视觉参照：一张整理有序的资料工作台，目录像抽屉，文件列表像铺开的目录卡，而不是企业后台报表。
- 用户、任务与环境：个人用户在桌面浏览器中长时间整理资料，也可能在窄窗口快速下载或分享。
- 设计转译：使用偏暖浅灰背景与墨绿色强调；列表信息密度适中；路径、文件名与主操作建立稳定水平节奏；边框和留白替代重阴影；动效仅解释弹层、上传进度和状态变化。
- 排除项：紫蓝渐变、玻璃拟态、满屏圆角卡片、虚构统计面板和装饰性大插画。
- 气质：安静、可靠、利落。

## Colors

墨绿色只用于主操作、选中导航、链接和焦点；中性色承担文件信息层级；成功、警告和危险色只用于明确状态。禁止为文件类型随意引入多套高饱和颜色。

## Typography

中文系统字体避免下载抖动。文件名使用正文 14px/500，元数据使用 12–13px；页标题 24px/600。容量和文件大小使用等宽数字特性。

## Layout

桌面使用 232px 固定侧栏和流式内容区，内容水平边距 32px；列表工具界面最大宽度 1440px。小于 900px 时侧栏转为抽屉，工具栏允许换行；小于 640px 时隐藏低优先级列并使用紧凑行操作。

管理后台使用 216px 固定侧栏与 56px 顶栏，内容区边距 24px。系统概览采用 `wide` 模式，最大宽度 1440px；用户管理和开放 API 属于数据列表，采用 `fluid` 模式使用全部可用工作区。小于 900px 时侧栏收起为 64px 图标导航，小于 640px 时转为顶部横向导航。后台页标题使用 20px/600，区块标题使用 16px/600。

## Elevation

页面与侧栏使用背景和 1px 边框分层。仅下拉菜单、Dialog、Drawer 和预览浮层使用中等级阴影。

## Shapes

控件 8px，独立浮层 12px，标签与头像可使用全圆角。文件列表本身不拆成悬浮卡片；状态不使用额外边缘色条重复编码。

## Components

页面壳、导航、工具栏、文件列表、容量条和空错状态使用自定义 CSS；Dialog、Dropdown、Upload、Pagination、Progress、Form 与 Tooltip 使用 Naive UI 并映射同一 Token。控件高度 40px，紧凑图标按钮 36px。

## Iconography

统一使用 `@vicons/tabler` 线性图标，通过 `AppIcon` 设置 SVG 尺寸。导航 20px、工具栏 18px、行内 16px；图标按钮至少 36px 且提供 `aria-label`。文件夹、上传、下载、分享、删除含义全局一致，不给普通图标套彩色底板。

## Patterns

- 登录：居中单面板，表单是唯一视觉主角。
- 文件列表：标题/容量、面包屑、工具栏、稳定列表、分页。
- 短表单：新建、重命名、移动与分享使用 Dialog。
- 详情：文件预览使用宽 Dialog，操作区保持稳定。

## Responsive

断点为 900px 和 640px。窄屏侧栏抽屉化、工具栏换行、文件元数据折叠；所有主要操作保持可见，触摸区域不小于 40px，页面不产生整页横向滚动。

## Implementation Mapping

- Token：`frontend/src/assets/styles/variables.scss`
- 全局规则：`frontend/src/assets/styles/global.scss`
- Naive UI 主题：`frontend/src/theme.ts`
- 代表页面：`frontend/src/pages/files/Index.vue`
