import React from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#b57edb',
          borderRadius: 12,
          colorBgContainer: '#ffffff',
          boxShadow: '0 4px 24px rgba(180, 126, 219, 0.1)',
        },
      }}
    >
      <div className="app-layout">
        <Sidebar />
        <ChatPanel />
      </div>
    </ConfigProvider>
  )
}

export default App
