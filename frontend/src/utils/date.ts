/** 界面统一使用北京时间格式化 ISO 日期。 */
export const formatTime = (value: string | null) =>
  value
    ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
    : '—';
