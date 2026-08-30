// WFlow-style form component registry (single source of truth for designer + renderer)
export const VALUE_TYPES = {
  String: '文本',
  Number: '数字',
  Array: '多选',
  Date: '日期',
  DateRange: '日期区间',
  User: '人员',
}

export const FORM_COMPONENTS = [
  { name: 'TextInput', title: '单行文本', valueType: 'String', icon: 'Edit', group: '基础组件' },
  { name: 'TextareaInput', title: '多行文本', valueType: 'String', icon: 'Document', group: '基础组件' },
  { name: 'NumberInput', title: '数字输入', valueType: 'Number', icon: 'Histogram', group: '基础组件' },
  { name: 'AmountInput', title: '金额输入', valueType: 'Number', icon: 'Money', group: '基础组件' },
  { name: 'SelectInput', title: '单选', valueType: 'String', icon: 'CircleCheck', group: '基础组件' },
  { name: 'MultipleSelect', title: '多选', valueType: 'Array', icon: 'Finished', group: '基础组件' },
  { name: 'DateTime', title: '日期', valueType: 'Date', icon: 'Calendar', group: '基础组件' },
  { name: 'DateTimeRange', title: '日期区间', valueType: 'DateRange', icon: 'Timer', group: '基础组件' },
  { name: 'UserPicker', title: '人员选择', valueType: 'User', icon: 'User', group: '高级组件' },
  { name: 'ImageUpload', title: '图片上传', valueType: 'Array', icon: 'Picture', group: '高级组件' },
  { name: 'FileUpload', title: '附件上传', valueType: 'Array', icon: 'Paperclip', group: '高级组件' },
  { name: 'TableList', title: '明细表格', valueType: 'Array', icon: 'Grid', group: '高级组件' },
  { name: 'Description', title: '说明文字', valueType: null, icon: 'Warning', group: '基础组件' },
]

const DEFAULT_PROPS = {
  placeholder: '',
  required: false,
  enablePrint: true,
  defaultValue: '',          // 默认值
  labelWidth: null,          // 标签宽度(空=跟随表单)
  hiddenLabel: false,        // 隐藏字段标签
  disabled: false,           // 是否禁用
  readonly: false,           // 是否只读
  requiredMsg: '',           // 必填校验提示
}

export function newFormItem(name) {
  const def = FORM_COMPONENTS.find((c) => c.name === name)
  const item = {
    id: `f_${name.toLowerCase().slice(0, 4)}_${Math.random().toString(36).slice(2, 6)}`,
    name: def.name,
    title: def.title,
    valueType: def.valueType,
    props: { ...DEFAULT_PROPS },
  }
  switch (name) {
    case 'TextInput':
      item.props.maxLength = 100
      item.props.clearable = true
      item.props.showWordLimit = false
      item.props.prepend = ''   // 前缀
      item.props.append = ''    // 后缀
      break
    case 'TextareaInput':
      item.props.rows = 3
      item.props.maxLength = 500
      item.props.showWordLimit = true
      item.props.autosize = false
      break
    case 'NumberInput':
      item.props.min = null
      item.props.max = null
      item.props.step = 1
      item.props.precision = 0
      item.props.controlsPosition = 'right'
      break
    case 'AmountInput':
      item.props.precision = 2
      item.props.showChinese = true
      item.props.min = 0
      break
    case 'SelectInput':
    case 'MultipleSelect':
      item.props.options = ['选项1', '选项2']
      item.props.expanding = false
      item.props.clearable = true
      item.props.filterable = false       // 可搜索
      item.props.multipleLimit = 0        // 多选数量限制(0不限)
      break
    case 'DateTime':
    case 'DateTimeRange':
      item.props.clearable = true
      break
    case 'DateTime':
      item.props.format = 'YYYY-MM-DD'
      break
    case 'DateTimeRange':
      item.props.format = 'YYYY-MM-DD HH:mm'
      break
    case 'UserPicker':
      item.props.multiple = false
      break
    case 'ImageUpload':
      item.props.maxNumber = 5
      item.props.maxSize = 5
      break
    case 'FileUpload':
      item.props.maxNumber = 5
      item.props.maxSize = 20
      item.props.fileTypes = []
      break
    case 'TableList':
      item.props.columns = [
        { id: 'c_' + Math.random().toString(36).slice(2, 6), title: '名称', name: 'TextInput' },
        { id: 'c_' + Math.random().toString(36).slice(2, 6), title: '数量', name: 'NumberInput' },
      ]
      item.props.maxSize = 0
      item.props.showBorder = true
      item.props.showSummary = false
      break
    case 'Description':
      item.props.content = '说明文字内容'
      break
  }
  return item
}

// comparisons available per value type (drives the condition editor)
export const COMPARE_BY_TYPE = {
  Number: [
    { value: '>', label: '>' }, { value: '>=', label: '≥' }, { value: '<', label: '<' },
    { value: '<=', label: '≤' }, { value: '==', label: '=' }, { value: 'between', label: '区间' },
  ],
  String: [
    { value: '==', label: '=' }, { value: 'in', label: '属于' },
  ],
  Date: [{ value: '==', label: '于' }],
  DateRange: [{ value: '==', label: '于' }],
  User: [
    { value: '==', label: '是' }, { value: '!=', label: '不是' },
  ],
  DateRange: [
    { value: '>=', label: '开始≥' }, { value: '>', label: '开始>' },
    { value: '<', label: '开始<' }, { value: '<=', label: '开始≤' },
    { value: '==', label: '开始=' },
  ],
  Array: [{ value: 'in', label: '包含任一' }],
}

export function defaultFieldId(name) {
  return `f_${name.toLowerCase().slice(0, 4)}_${Math.random().toString(36).slice(2, 6)}`
}
