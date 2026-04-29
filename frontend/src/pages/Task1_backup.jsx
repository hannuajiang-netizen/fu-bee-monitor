import React, { useState } from 'react'
import { Card, Upload, Button, Table, message, Spin, Typography, Row, Col } from 'antd'
import { InboxOutlined, CopyOutlined, RocketOutlined } from '@ant-design/icons'
import axios from 'axios'

const { Dragger } = Upload
const { Title, Text } = Typography
const { TextArea } = Typography

// 25列定义
const columns = [
  { title: '日期', dataIndex: '日期', key: '日期', fixed: 'left', width: 120 },
  { title: '活跃用户数', dataIndex: '活跃用户数', key: '活跃用户数', width: 120 },
  { title: '人均停留时长min', dataIndex: '人均停留时长min', key: '人均停留时长min', width: 150 },
  { title: '互动次数', dataIndex: '互动次数', key: '互动次数', width: 100 },
  { title: '互动人数', dataIndex: '互动人数', key: '互动人数', width: 100 },
  { title: '互动人数占比', dataIndex: '互动人数占比', key: '互动人数占比', width: 120 },
  { title: '分享人数', dataIndex: '分享人数', key: '分享人数', width: 100 },
  { title: '关注人数', dataIndex: '关注人数', key: '关注人数', width: 100 },
  { title: '次日留存率', dataIndex: '次日留存率', key: '次日留存率', width: 120 },
  { title: '3留率', dataIndex: '3留率', key: '3留率', width: 100 },
  { title: '7留率', dataIndex: '7留率', key: '7留率', width: 100 },
  { title: '14留率', dataIndex: '14留率', key: '14留率', width: 100 },
  { title: '30日留率', dataIndex: '30日留率', key: '30日留率', width: 120 },
  { title: '当日发布笔记量', dataIndex: '当日发布笔记量', key: '当日发布笔记量', width: 130 },
  { title: '当日发布笔记用户数', dataIndex: '当日发布笔记用户数', key: '当日发布笔记用户数', width: 160 },
  { title: '累计发布笔记量', dataIndex: '累计发布笔记量', key: '累计发布笔记量', width: 130 },
  { title: '累计发布笔记用户数', dataIndex: '累计发布笔记用户数', key: '累计发布笔记用户数', width: 160 },
  { title: '活跃在群用户数', dataIndex: '活跃在群用户数', key: '活跃在群用户数', width: 140 },
  { title: '群活跃用户数', dataIndex: '群活跃用户数', key: '群活跃用户数', width: 120 },
  { title: '群发言用户数', dataIndex: '群发言用户数', key: '群发言用户数', width: 120 },
  { title: '活跃在蜂巢用户数', dataIndex: '活跃在蜂巢用户数', key: '活跃在蜂巢用户数', width: 150 },
  { title: '蜂巢活跃用户数', dataIndex: '蜂巢活跃用户数', key: '蜂巢活跃用户数', width: 140 },
  { title: '发布蜂巢笔记用户数', dataIndex: '发布蜂巢笔记用户数', key: '发布蜂巢笔记用户数', width: 160 },
  { title: '预留1', dataIndex: '预留1', key: '预留1', width: 100 },
  { title: '预留2', dataIndex: '预留2', key: '预留2', width: 100 },
]

function Task1() {
  const [files, setFiles] = useState({
    user_basic: null,
    content_produce: null,
    school_detail: null
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  const handleFileChange = (field, info) => {
    const { file } = info
    if (file.status === 'done' || file.status === 'uploading' || !file.status) {
      setFiles(prev => ({ ...prev, [field]: file }))
    }
  }

  const canAnalyze = files.user_basic && files.content_produce && files.school_detail

  const handleAnalyze = async () => {
    if (!canAnalyze) {
      message.warning('请先上传所有3个文件')
      return
    }

    setLoading(true)
    const formData = new FormData()
    formData.append('user_basic', files.user_basic.originFileObj || files.user_basic)
    formData.append('content_produce', files.content_produce.originFileObj || files.content_produce)
    formData.append('school_detail', files.school_detail.originFileObj || files.school_detail)

    try {
      const response = await axios.post('/api/task1/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      if (response.data.success) {
        setResult(response.data)
        message.success('分析完成！')
      } else {
        message.error(response.data.error || '分析失败')
      }
    } catch (error) {
      message.error(error.response?.data?.error || '请求失败')
    } finally {
      setLoading(false)
    }
  }

  const copyTable = () => {
    if (!result?.summary_table) return
    
    const headers = columns.map(col => col.title).join('\t')
    const rows = result.summary_table.map(row => 
      columns.map(col => row[col.dataIndex] || '').join('\t')
    ).join('\n')
    
    const text = headers + '\n' + rows
    navigator.clipboard.writeText(text)
    message.success('表格已复制到剪贴板')
  }

  const copyText = () => {
    if (!result?.weekly_report) return
    navigator.clipboard.writeText(result.weekly_report)
    message.success('文本已复制到剪贴板')
  }

  const uploadProps = (field) => ({
    name: field,
    multiple: false,
    beforeUpload: () => false,
    onChange: (info) => handleFileChange(field, info),
    fileList: files[field] ? [files[field]] : []
  })

  return (
    <div>
      <Title level={4}>校园认证用户DAU监控</Title>
      
      {/* 上传区域 */}
      <Card title="📁 上传数据文件" style={{ marginBottom: 24 }}>
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ textAlign: 'center', marginBottom: 8 }}>
              <Text strong>📁 用户基本情况</Text>
            </div>
            <Dragger {...uploadProps('user_basic')} accept=".xlsx,.xls">
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此处</p>
              <p className="ant-upload-hint">支持 .xlsx / .xls 格式</p>
            </Dragger>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center', marginBottom: 8 }}>
              <Text strong>📁 内容生产情况</Text>
            </div>
            <Dragger {...uploadProps('content_produce')} accept=".xlsx,.xls">
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此处</p>
              <p className="ant-upload-hint">支持 .xlsx / .xls 格式</p>
            </Dragger>
          </Col>
          <Col span={8}>
            <div style={{ textAlign: 'center', marginBottom: 8 }}>
              <Text strong>📁 累计单校情况</Text>
            </div>
            <Dragger {...uploadProps('school_detail')} accept=".xlsx,.xls">
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽文件到此处</p>
              <p className="ant-upload-hint">支持 .xlsx / .xls 格式</p>
            </Dragger>
          </Col>
        </Row>
        
        <div style={{ textAlign: 'center', marginTop: 24 }}>
          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            onClick={handleAnalyze}
            loading={loading}
            disabled={!canAnalyze}
          >
            🚀 开始分析
          </Button>
        </div>
      </Card>

      {/* 结果区域 */}
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin size="large" />
          <p style={{ marginTop: 16 }}>正在分析数据...</p>
        </div>
      )}

      {result && (
        <>
          {/* 汇总表格 */}
          <Card 
            title="📊 近14天汇总表" 
            style={{ marginBottom: 24 }}
            extra={
              <Button icon={<CopyOutlined />} onClick={copyTable}>
                📋 复制表格
              </Button>
            }
          >
            <Table
              dataSource={result.summary_table}
              columns={columns}
              rowKey="日期"
              scroll={{ x: 3000 }}
              pagination={false}
              size="small"
            />
          </Card>

          {/* 周报文本 */}
          <Card
            title="📝 周报结论文本"
            extra={
              <Button icon={<CopyOutlined />} onClick={copyText}>
                📋 复制文本
              </Button>
            }
          >
            <TextArea
              value={result.weekly_report}
              rows={8}
              readOnly
              style={{ 
                background: '#f5f5f5', 
                fontFamily: 'monospace',
                fontSize: 14
              }}
            />
          </Card>
        </>
      )}
    </div>
  )
}

export default Task1