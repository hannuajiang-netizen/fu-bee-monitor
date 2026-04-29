import React from 'react'
import { Layout, Menu } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  BarChartOutlined,
  SyncOutlined,
  AimOutlined
} from '@ant-design/icons'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/task1',
    icon: <BarChartOutlined />,
    label: '校园认证用户DAU监控',
  },
  {
    key: '/task2',
    icon: <SyncOutlined />,
    label: '大盘DAU监控',
  },
  {
    key: '/task3',
    icon: <AimOutlined />,
    label: '社团活动拉新监控',
  },
]

function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        background: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: 64,
        borderBottom: '1px solid #f0f0f0',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000
      }}>
        <h1 style={{
          margin: 0,
          fontSize: 18,
          fontWeight: 'bold',
          color: '#001529'
        }}>
          🦞 fu之小蜜蜂监控后台
        </h1>
      </Header>
      
      <Layout style={{ marginTop: 64 }}>
        <Sider
          width={220}
          style={{
            background: '#001529',
            position: 'fixed',
            left: 0,
            top: 64,
            bottom: 0,
            overflow: 'auto'
          }}
        >
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname === '/' ? '/task1' : location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ borderRight: 0 }}
          />
        </Sider>
        
        <Layout style={{ marginLeft: 220 }}>
          <Content style={{
            margin: 24,
            padding: 24,
            background: '#fff',
            minHeight: 280,
            borderRadius: 8
          }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}

export default MainLayout