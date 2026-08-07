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
          colorPrimary: '#1677ff',
          borderRadius: 8,
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
