import React, { useState, useEffect } from 'react'
import { Card, Input, Button, Row, Col, Typography, Alert, Tag, message } from 'antd'
import { CopyOutlined, SyncOutlined, FileTextOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Title, Text } = Typography
const { TextArea } = Input

// 10个字段定义
const FIELDS = [
  { key: 'dau', label: 'DAU（设备）' },
  { key: 'retention', label: '次留' },
  { key: 'new_user_dau', label: '新用户DAU（设备）' },
  { key: 'avg_duration', label: '人均访问时长(min)' },
  { key: 'interaction_users', label: '互动用户数' },
  { key: 'interaction_ratio', label: '互动用户占比' },
  { key: 'produce_users', label: '生产笔记用户数' },
  { key: 'produce_ratio', label: '生产笔记用户占比' },
  { key: 'consume_ratio', label: '消费用户占比' },
  { key: 'school_auth_ratio', label: '日活学校认证用户数占比' },
]

function Task2() {
  // 功能区1状态
  const [rawText, setRawText] = useState('')
  const [convertedText, setConvertedText] = useState('')
  const [lastWeekData, setLastWeekData] = useState({})

  // 功能区2状态
  const [thisWeekValues, setThisWeekValues] = useState({})
  const [pasteInput, setPasteInput] = useState('')
  const [output1, setOutput1] = useState('')
  const [output2, setOutput2] = useState('')
  const [topChannels, setTopChannels] = useState([])

  // 加载任务三的TOP渠道
  useEffect(() => {
    loadTopChannels()
  }, [])

  const loadTopChannels = async () => {
    try {
      const response = await axios.get('/api/task3/latest_top_channels')
      if (response.data && response.data.top_channels) {
        setTopChannels(response.data.top_channels.slice(0, 4))
      }
    } catch (error) {
      // 未执行过任务三，忽略错误
    }
  }

  // 功能区1：转换数据位置
  const handleConvert = () => {
    if (!rawText.trim()) {
      message.warning('请先粘贴原始数据')
      return
    }

    // 正则匹配：指标名 + 本周数值 + （上周 旧数值）
    const pattern = /([^（；，,]+?)([\d.]+%?min?)（上周[\d.]+%?min?）/g
    
    let converted = rawText
    const extracted = {}

    // 提取本周数据
    let match
    const regex = new RegExp(pattern.source, 'g')
    while ((match = regex.exec(rawText)) !== null) {
      const fullMatch = match[0]
      const indicator = match[1].trim()
      const thisWeekValue = match[2]
      
      // 转换格式：本周数据变成下周的"上周数据"
      const newFormat = `${indicator}（上周${thisWeekValue}）`
      converted = converted.replace(fullMatch, newFormat)
      
      // 提取纯数字保存
      const pureValue = thisWeekValue.replace(/[^\d.]/g, '')
      
      // 映射到字段
      if (indicator.includes('DAU')) extracted['日均DAU'] = pureValue
      if (indicator.includes('次留')) extracted['次留'] = pureValue
      if (indicator.includes('新用户')) extracted['新用户DAU'] = pureValue
      if (indicator.includes('时长')) extracted['人均访问时长'] = pureValue
      if (indicator.includes('互动用户') && !indicator.includes('占比')) extracted['互动用户数'] = pureValue
      if (indicator.includes('生产') && indicator.includes('用户') && !indicator.includes('占比')) extracted['生产笔记用户数'] = pureValue
    }

    setConvertedText(converted)
    setLastWeekData(extracted)
    message.success('转换完成！')
  }

  // 功能区2：处理粘贴输入
  const handlePaste = () => {
    if (!pasteInput.trim()) {
      message.warning('请先粘贴数据')
      return
    }

    // 按Tab或空格分割
    const values = pasteInput.split(/[\t\s]+/).filter(v => v.trim())
    
    const newValues = {}
    FIELDS.forEach((field, index) => {
      if (values[index]) {
        // 去除千位分隔符
        newValues[field.key] = values[index].replace(/,/g, '')
      }
    })
    
    setThisWeekValues(newValues)
    message.success('数据已填入')
  }

  // 生成周报话术
  const generateReport = () => {
    // 检查必填字段
    const required = ['dau', 'retention', 'new_user_dau', 'avg_duration', 'interaction_users', 'produce_users']
    const missing = required.filter(key => !thisWeekValues[key])
    
    if (missing.length > 0) {
      message.warning(`请填写以下字段: ${missing.map(k => FIELDS.find(f => f.key === k).label).join(', ')}`)
      return
    }

    const v = thisWeekValues
    const o = lastWeekData

    // 输出1：本周周报话术
    const report1 = `日均DAU ${v.dau}（上周${o['日均DAU'] || '—'}），人均消费时长${v.avg_duration}min（上周${o['人均访问时长'] || '—'}），次留${v.retention}%（上周${o['次留'] || '—'}%）；日均新用户DAU数${v.new_user_dau}（上周${o['新用户DAU'] || '—'}），日均互动用户数${v.interaction_users}（上周${o['互动用户数'] || '—'}），日均生产笔记用户数${v.produce_users}（上周${o['生产笔记用户数'] || '—'}）`

    // 简化渠道名称
    const simplifyChannel = (name) => {
      return name
        .replace(/^userteam_/, '')
        .replace(/^act_white_/, '')
        .replace(/^group_/, '')
        .replace(/^search_/, '')
    }

    // 输出2：转换后的上周格式
    let topChannelsText = ''
    if (topChannels.length > 0) {
      const channelNames = topChannels.map(ch => simplifyChannel(ch['渠道名称'] || ch.channel_name || ch.name || '未知'))
      topChannelsText = channelNames.join('、')
    }

    const report2 = `日均DAU（上周${v.dau}）
人均消费时长（上周${v.avg_duration}min），次留（上周${v.retention}%）；
日均生产用户数（上周${v.produce_users}），日均互动用户数（上周${v.interaction_users}）；
日均新增注册账号数（上周${v.new_user_dau}）
${topChannels.length > 0 
  ? `本周主要由${topChannelsText}带来新增。` 
  : '本周主要由______带来新增。（⚠️ 请先在「社团活动拉新监控」中执行分析）'}`

    setOutput1(report1)
    setOutput2(report2)
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  }

  return (
    <div>
      <Title level={4}>大盘DAU监控</Title>

      {/* 功能区1：数据位置转换 */}
      <Card title="🔄 功能区 1：数据位置转换" style={{ marginBottom: 24 }}>
        <Row gutter={24}>
          <Col span={10}>
            <Text strong>粘贴原始数据</Text>
            <TextArea
              value={rawText}
              onChange={e => setRawText(e.target.value)}
              rows={8}
              placeholder="例如：日均DAU 66499（上周62522）人均消费时长5.17min（上周5.76）..."
              style={{ marginTop: 8 }}
            />
          </Col>
          <Col span={4} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Button type="primary" icon={<SyncOutlined />} onClick={handleConvert} size="large">
              转换
            </Button>
          </Col>
          <Col span={10}>
            <Text strong>转换结果</Text>
            <TextArea
              value={convertedText}
              rows={8}
              readOnly
              style={{ marginTop: 8, background: '#f5f5f5' }}
            />
            {convertedText && (
              <Button 
                icon={<CopyOutlined />} 
                onClick={() => copyToClipboard(convertedText)}
                style={{ marginTop: 8 }}
                size="small"
              >
                复制
              </Button>
            )}
          </Col>
        </Row>
      </Card>

      {/* 功能区2：新数据填入模板 */}
      <Card title="📝 功能区 2：新数据填入模板">
        {/* 上周数据展示 */}
        {Object.keys(lastWeekData).length > 0 && (
          <Alert
            message={
              <div>
                <Text strong>上周数据：</Text>
                {Object.entries(lastWeekData).map(([key, value]) => (
                  <Tag key={key} color="blue" style={{ margin: '0 4px 4px 0' }}>
                    {key}={value}
                  </Tag>
                ))}
              </div>
            }
            type="info"
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 本周新数据输入 */}
        <Card type="inner" title="📊 本周新数据输入" style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 16 }}>
            <Text strong>请粘贴本周数据（按字段顺序，Tab分隔或空格分隔均可）</Text>
            <Input
              value={pasteInput}
              onChange={e => setPasteInput(e.target.value)}
              placeholder="例如：66499 57.75% 9162 5.17 17674 26.33% 11969 17.83% 49.09% 15.89%"
              style={{ marginTop: 8 }}
              addonAfter={<Button type="primary" size="small" onClick={handlePaste}>一键填入</Button>}
            />
          </div>

          <Row gutter={[16, 16]}>
            {FIELDS.map(field => (
              <Col span={6} key={field.key}>
                <div style={{ marginBottom: 4 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>{field.label}</Text>
                </div>
                <Input
                  value={thisWeekValues[field.key] || ''}
                  onChange={e => setThisWeekValues(prev => ({ ...prev, [field.key]: e.target.value }))}
                  placeholder="输入数值"
                  size="small"
                />
              </Col>
            ))}
          </Row>
        </Card>

        {/* 生成按钮 */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <Button type="primary" size="large" icon={<FileTextOutlined />} onClick={generateReport}>
            生成周报话术
          </Button>
        </div>

        {/* 输出区域 */}
        {output1 && (
          <>
            <Card
              title="📋 输出 1：本周周报话术"
              style={{ marginBottom: 16 }}
              extra={
                <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(output1)} size="small">
                  复制
                </Button>
              }
            >
              <TextArea value={output1} rows={4} readOnly style={{ background: '#f5f5f5' }} />
            </Card>

            <Card
              title="📋 输出 2：转换后的上周格式（供下周使用）"
              extra={
                <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(output2)} size="small">
                  复制
                </Button>
              }
            >
              <TextArea value={output2} rows={8} readOnly style={{ background: '#f5f5f5', fontFamily: 'monospace' }} />
            </Card>
          </>
        )}
      </Card>
    </div>
  )
}

export default Task2