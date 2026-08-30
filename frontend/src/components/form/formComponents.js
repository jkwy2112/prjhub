// WFlow-style form component registry (single source of truth for designer + renderer)
export const VALUE_TYPES = {
  String: '文本',
  Number: '数字',
  Array: '多选',
  Date: '日期',
  User: '人员',
}

export const FORM_COMPONENTS = [
  { name: 'TextInput', title: '单行文本', valueType: 'String', icon: 'Edit' },
  { name: 'TextareaInput', title: '多行文本', valueType: 'String', icon: 'Document' },
  { name: 'NumberInput', title: '数字输入', valueType: 'Number', icon: 'Histogram' },
  { name: 'AmountInput', title: '金额输入', valueType: 'Number', icon: 'Money' },
  { name: 'SelectInput', title: '单选', valueType: 'String', icon: 'CircleCheck' },
  { name: 'MultipleSelect', title: '多选', valueType: 'Array', icon: 'Finished' },
  { name: 'DateTime', title: '日期', valueType: 'Date', icon: 'Calendar' },
  { name: 'UserPicker', title: '人员选择', valueType: 'User', icon: 'User' },
  { name: 'Description', title: '说明文字', valueType: null, icon: 'Warning' },
]

export function newFormItem(name) {
  const def = FORM_COMPONENTS.find((c) => c.name === name)
  const item = {
    id: `f_${name.toLowerCase().slice(0, 4)}_${Math.random().toString(36).slice(2, 6)}`,
    name: def.name,
    title: def.title,
    valueType: def.valueType,
    props: { required: false, placeholder: '' },
  }
  if (name === 'SelectInput' || name === 'MultipleSelect') {
    item.props.options = ['选项1', '选项2']
  }
  if (name === 'Description') {
    item.props.content = '说明文字内容'
  }
  if (name === 'UserPicker') {
    item.props.multiple = false
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
  User: [{ value: '==', label: '是' }],
  Array: [{ value: 'in', label: '包含任一' }],
}

export function defaultFieldId(name) {
  return `f_${name.toLowerCase().slice(0, 4)}_${Math.random().toString(36).slice(2, 6)}`
}
