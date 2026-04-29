import React, { useState, useEffect } from 'react'
import { 
  Card, Upload, Button, Table, message, Spin, Typography, 
  DatePicker, Checkbox, Row, Col, Tag, Modal, Input, Alert 
} from 'antd'
import { 
  InboxOutlined, CopyOutlined, RocketOutlined, 
  PlusOutlined, DeleteOutlined, CheckSquareOutlined 
} from '@ant-design/icons'
import axios from 'axios'
import dayjs from 'dayjs'

const { Dragger } = Upload
const { Title, Text } = Typography
const { RangePicker } = DatePicker

function Task3() {
  const [file, setFile] = useState(null)
  const [dateRange, setDateRange] = useState([dayjs('2025-04-01'), dayjs()])
  const [channels, setChannels] = useState([])
  const [selectedChannels, setSelectedChannels] = useState([])
  const [loading, setLoading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [newChannelsFound, setNewChannelsFound] = useState([])
  
  // 新增渠道弹窗
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [newChannelName, setNewChannelName] = useState('')

  // 加载渠道列表
  useEffect(() => {
    loadChannels()
  }, [])

  const loadChannels = async () => {
    setLoading(true)
    try {
      const response = await axios.get('/api/task3/channels')
      const data = response.data
      if (data.channels) {
        setChannels(data.channels)
        setSelectedChannels(data.channels.filter(ch => 
          !ch.is_default || data.channels.indexOf(ch) < 19
        ).map(ch => ch.name))
      }
    } catch (error) {
      message.error('加载渠道列表失败')
    } finally {
      setLoading(false)
    }
  }

  const saveChannels = async (newChannels) => {
    try {
      await axios.post('/api/task3/channels', { channels: newChannels })
    } catch (error) {
      message.error('保存渠道列表失败')
    }
  }

  const handleFileChange = (info) => {
    const { file } = info
    if (file.status === 'done' || file.status === 'uploading' || !file.status) {
      setFile(file)
    }
  }

  const handleAnalyze = async () => {
    if (!file) {
      message.warning('请先上传Excel文件')
      return
    }
    if (selectedChannels.length === 0) {
      message.warning('请至少选择一个渠道')
      return
    }

    setAnalyzing(true)
    const formData = new FormData()
    formData.append('excel_file', file.originFileObj || file)
    
    const params = {
      start_date: dateRange[0].format('YYYY-MM-DD'),
      end_date: dateRange[1].format('YYYY-MM-DD'),
      selected_channels: selectedChannels
    }
    formData.append('params', JSON.stringify(params))

    try {
      const response = await axios.post('/api/task3/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      if (response.data.success) {
        setResult(response.data)
        
        // 处理新发现的渠道
        if (response.data.new_channels_found && response.data.new_channels_found.length > 0) {
          setNewChannelsFound(response.data.new_channels_found)
          
          // 自动添加新渠道到列表
          const newChannelObjs = response.data.new_channels_found.map(name => ({
            name,
            is_default: false,
            is_new: true
          }))
          
          const updatedChannels = [...channels, ...newChannelObjs]
          setChannels(updatedChannels)
          setSelectedChannels([...selectedChannels, ...response.data.new_channels_found])
          saveChannels(updatedChannels)
          
          message.success(`分析完成！发现 ${response.data.new_channels_found.length} 个新渠道已自动添加`)
        } else {
          message.success('分析完成！')
        }
      } else {
        message.error(response.data.error || '分析失败')
      }
    } catch (error) {
      message.error(error.response?.data?.error || '请求失败')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleSelectAll = () => {
    setSelectedChannels(channels.map(ch => ch.name))
  }

  const handleDeselectAll = () => {
    setSelectedChannels([])
  }

  const handleChannelToggle = (channelName, checked) => {
    if (checked) {
      setSelectedChannels([...selectedChannels, channelName])
    } else {
      setSelectedChannels(selectedChannels.filter(name => name !== channelName))
    }
  }

  const handleAddChannel = () => {
    if (!newChannelName.trim()) {
      message.warning('请输入渠道名称')
      return
    }
    
    if (channels.some(ch => ch.name === newChannelName.trim())) {
      message.warning('该渠道已存在')
      return
    }
    
    const newChannel = {
      name: newChannelName.trim(),
      is_default: false,
      is_new: false
    }
    
    const updatedChannels = [...channels, newChannel]
    setChannels(updatedChannels)
    setSelectedChannels([...selectedChannels, newChannel.name])
    saveChannels(updatedChannels)
    
    setNewChannelName('')
    setIsModalOpen(false)
    message.success('渠道已添加')
  }

  const handleDeleteChannel = (channelName) => {
    const channel = channels.find(ch => ch.name === channelName)
    if (channel && channel.is_default) {
      message.warning('预置渠道不能删除')
      return
    }
    
    const updatedChannels = channels.filter(ch => ch.name !== channelName)
    setChannels(updatedChannels)
    setSelectedChannels(selectedChannels.filter(name => name !== channelName))
    saveChannels(updatedChannels)
    message.success('渠道已删除')
  }

  const copyToClipboard = (data, type) => {
    let text = ''
    
    if (type === 'top10') {
      text = '排名\t渠道名称\t拉新人数\n'
      text += data.map(row => `${row['排名']}\t${row['渠道名称']}\t${row['拉新人数']}`).join('\n')
    } else if (type === 'summary') {
      const entries = Object.entries(data)
      text = entries.map(([k, v]) => `${k}: ${v}`).join('\n')
    } else if (type === 'detail') {
      const headers = ['渠道名称', '拉新人数', '人均时长', '次留', '3留', '7留', '14留', '30留']
      text = headers.join('\t') + '\n'
      text += data.map(row => headers.map(h => row[h] || '').join('\t')).join('\n')
    }
    
    navigator.clipboard.writeText(text)
    message.success('已复制到剪贴板')
  }

  // 表格列定义
  const top10Columns = [
    { title: '排名', dataIndex: '排名', key: '排名', width: 80 },
    { title: '渠道名称', dataIndex: '渠道名称', key: '渠道名称' },
    { title: '拉新人数', dataIndex: '拉新人数', key: '拉新人数', align: 'right' },
  ]

  const detailColumns = [
    { title: '渠道名称', dataIndex: '渠道名称', key: '渠道名称', width: 200 },
    { title: '拉新人数', dataIndex: '拉新人数', key: '拉新人数', align: 'right', width: 100 },
    { title: '人均时长', dataIndex: '人均时长', key: '人均时长', align: 'right', width: 100 },
    { title: '次留', dataIndex: '次留', key: '次留', align: 'right', width: 80 },
    { title: '3留', dataIndex: '3留', key: '3留', align: 'right', width: 80 },
    { title: '7留', dataIndex: '7留', key: '7留', align: 'right', width: 80 },
    { title: '14留', dataIndex: '14留', key: '14留', align: 'right', width: 80 },
    { title: '30留', dataIndex: '30留', key: '30留', align: 'right', width: 80 },
  ]

  return (
    <div>
      <Title level={4}>社团活动拉新监控</Title>

      {/* 上传区域 */}
      <Card title="📁 上传拉新数据报表 Excel" style={{ marginBottom: 24 }}>
        <Dragger
          name="excel_file"
          multiple={false}
          beforeUpload={() => false}
          onChange={handleFileChange}
          accept=".xlsx,.xls"
          fileList={file ? [file] : []}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处</p>
          <p className="ant-upload-hint">支持 .xlsx / .xls 格式，应包含：拉新日期、拉新归属、拉新人数、留存率等字段</p>
        </Dragger>
      </Card>

      {/* 时间范围选择 */}
      <Card title="📅 时间范围" style={{ marginBottom: 24 }}>
        <RangePicker
          value={dateRange}
          onChange={setDateRange}
          style={{ width: 300 }}
        />
      </Card>

      {/* 渠道选择 */}
      <Card 
        title={
          <span>
            <CheckSquareOutlined style={{ marginRight: 8 }} />
            选择统计渠道
          </span>
        }
        style={{ marginBottom: 24 }}
        extra={
          <div>
            <Button size="small" onClick={handleSelectAll} style={{ marginRight: 8 }}>全选</Button>
            <Button size="small" onClick={handleDeselectAll} style={{ marginRight: 8 }}>取消全选</Button>
            <Button size="small" icon={<PlusOutlined />} onClick={() => setIsModalOpen(true)}>新增渠道</Button>
          </div>
        }
      >
        {newChannelsFound.length > 0 && (
          <Alert
            message={`发现 ${newChannelsFound.length} 个新渠道已自动添加`}
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        
        <div style={{ maxHeight: 400, overflow: 'auto' }}>
          {channels.map(channel => (
            <div 
              key={channel.name} 
              style={{ 
                padding: '8px 0', 
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              <Checkbox
                checked={selectedChannels.includes(channel.name)}
                onChange={e => handleChannelToggle(channel.name, e.target.checked)}
                style={{ flex: 1 }}
              >
                {channel.is_new && <Tag color="green" style={{ marginRight: 8 }}>🆕</Tag>}
                {channel.name}
              </Checkbox>
              {!channel.is_default && (
                <Button
                  type="text"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => handleDeleteChannel(channel.name)}
                />
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* 分析按钮 */}
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <Button
          type="primary"
          size="large"
          icon={<RocketOutlined />}
          onClick={handleAnalyze}
          loading={analyzing}
          disabled={!file || selectedChannels.length === 0}
        >
          🚀 开始分析
        </Button>
      </div>

      {/* 结果区域 */}
      {analyzing && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>正在分析数据...</p>
        </div>
      )}

      {result && (
        <>
          {/* TOP10 渠道 */}
          <Card
            title="🏆 近一周拉新 TOP10"
            style={{ marginBottom: 24 }}
            extra={
              <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(result.top10, 'top10')}>
                复制
              </Button>
            }
          >
            <Table
              dataSource={result.top10}
              columns={top10Columns}
              rowKey="排名"
              pagination={false}
              size="small"
            />
          </Card>

          {/* 整体汇总 */}
          <Card
            title="📊 勾选渠道整体汇总"
            style={{ marginBottom: 24 }}
            extra={
              <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(result.overall_summary, 'summary')}>
                复制
              </Button>
            }
          >
            <Row gutter={[16, 16]}>
              {Object.entries(result.overall_summary).map(([key, value]) => (
                <Col span={6} key={key}>
                  <Card size="small" style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{key}</Text>
                    <div style={{ fontSize: 20, fontWeight: 'bold', marginTop: 8 }}>{value}</div>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>

          {/* 各渠道明细 */}
          <Card
            title="📋 各渠道明细"
            extra={
              <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(result.channel_detail, 'detail')}>
                复制
              </Button>
            }
          >
            <Table
              dataSource={result.channel_detail}
              columns={detailColumns}
              rowKey="渠道名称"
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </>
      )}

      {/* 新增渠道弹窗 */}
      <Modal
        title="新增渠道"
        open={isModalOpen}
        onOk={handleAddChannel}
        onCancel={() => {
          setIsModalOpen(false)
          setNewChannelName('')
        }}
      >
        <Input
          placeholder="请输入渠道名称"
          value={newChannelName}
          onChange={e => setNewChannelName(e.target.value)}
          onPressEnter={handleAddChannel}
        />
      </Modal>
    </div>
  )
}

export default Task3