// 与后端 TextChoices 保持一致的前端字典
export const GRANARY_TYPE = [
  { value: 'square', label: '平房仓' },
  { value: 'silo', label: '立筒仓' },
  { value: 'underground', label: '地下仓' },
  { value: 'shallow', label: '浅圆仓' },
]

export const GRANARY_STATUS = [
  { value: 'empty', label: '空仓', type: 'info' },
  { value: 'storing', label: '在储', type: 'success' },
  { value: 'fumigating', label: '熏蒸中', type: 'warning' },
  { value: 'maintenance', label: '检修', type: 'danger' },
]

export const GRAIN_KIND = [
  { value: 'wheat', label: '小麦' },
  { value: 'rice', label: '稻谷' },
  { value: 'corn', label: '玉米' },
  { value: 'soybean', label: '大豆' },
  { value: 'paddy', label: '水稻' },
]

export const GRADE = [
  { value: '1', label: '一等' },
  { value: '2', label: '二等' },
  { value: '3', label: '三等' },
  { value: '4', label: '四等' },
  { value: '5', label: '五等' },
]

export const ALERT_LEVEL = [
  { value: 'normal', label: '正常', type: 'success' },
  { value: 'warning', label: '预警', type: 'warning' },
  { value: 'critical', label: '告警', type: 'danger' },
]

export const DIRECTION = [
  { value: 'in', label: '入库', type: 'success' },
  { value: 'out', label: '出库', type: 'danger' },
]

export const BIZ_TYPE = [
  { value: 'purchase', label: '收购入库' },
  { value: 'transfer_in', label: '调拨入仓' },
  { value: 'return', label: '退货入库' },
  { value: 'sale', label: '销售出库' },
  { value: 'transfer_out', label: '调出出仓' },
  { value: 'loss', label: '损耗出库' },
  { value: 'process', label: '加工出库' },
]

export const FUMIGATION_AGENT = [
  { value: 'ph3', label: '磷化氢(环流熏蒸)' },
  { value: 'alp', label: '磷化铝片剂' },
  { value: 'co2', label: '气调(二氧化碳)' },
  { value: 'other', label: '其他药剂' },
]

export const FUMIGATION_STATUS = [
  { value: 'planned', label: '已安排', type: 'info' },
  { value: 'running', label: '施药中', type: 'warning' },
  { value: 'sealed', label: '密闭中', type: 'primary' },
  { value: 'ventilating', label: '通风散气', type: 'warning' },
  { value: 'done', label: '已完成', type: 'success' },
  { value: 'canceled', label: '已取消', type: 'danger' },
]

export const STOCKTAKE_STATUS = [
  { value: 'draft', label: '草稿', type: 'info' },
  { value: 'counting', label: '盘点中', type: 'warning' },
  { value: 'finished', label: '已完成', type: 'primary' },
  { value: 'adjusted', label: '已调账', type: 'success' },
]

export const findLabel = (dict, value) =>
  dict.find((d) => d.value === value)?.label ?? value
export const findType = (dict, value) =>
  dict.find((d) => d.value === value)?.type ?? ''
