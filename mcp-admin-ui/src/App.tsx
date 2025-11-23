/**
 * MCP Enterprise Server 管理UI - 主应用
 */

import { useEffect, useState } from 'react';
import { Layout, Typography, Badge, Space, Spin, Button, message } from 'antd';
import {
  ApiOutlined,
  SettingOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import './App.css';
import Dashboard from './pages/Dashboard';
import { getWebSocketClient } from './services/websocket';

const { Header, Content, Footer } = Layout;
const { Title, Text } = Typography;

function App() {
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reconnecting, setReconnecting] = useState(false);

  const connectWebSocket = async () => {
    const wsClient = getWebSocketClient();

    try {
      setReconnecting(true);
      await wsClient.connect();
      setConnected(true);
      setLoading(false);

      // 订阅所有频道
      wsClient.subscribe('error_firewall');
      wsClient.subscribe('db_pool_stats');
      wsClient.subscribe('vector_search');
      wsClient.subscribe('system_alerts');
      wsClient.subscribe('ai_analysis');
      wsClient.subscribe('memory_updates');
      wsClient.subscribe('system_stats');  // 新增系统统计频道

      message.success('WebSocket 连接成功');
    } catch (err) {
      console.error('WebSocket连接失败:', err);
      setConnected(false);
      setLoading(false);
      message.error('WebSocket 连接失败');
    } finally {
      setReconnecting(false);
    }
  };

  const handleReconnect = () => {
    const wsClient = getWebSocketClient();
    wsClient.disconnect();
    connectWebSocket();
  };

  useEffect(() => {
    connectWebSocket();

    // 清理
    return () => {
      const wsClient = getWebSocketClient();
      wsClient.disconnect();
    };
  }, []);

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: '#001529',
        padding: '0 24px'
      }}>
        <Space size="large">
          <ApiOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
          <Title level={3} style={{ margin: 0, color: 'white' }}>
            MCP Enterprise Server
          </Title>
        </Space>

        <Space>
          <Badge
            status={connected ? 'success' : 'error'}
            text={
              <Text style={{ color: 'white' }}>
                {connected ? 'WebSocket已连接' : 'WebSocket断开'}
              </Text>
            }
          />
          {!connected && (
            <Button
              type="primary"
              size="small"
              icon={<ReloadOutlined />}
              loading={reconnecting}
              onClick={handleReconnect}
            >
              重连
            </Button>
          )}
          <SettingOutlined style={{ fontSize: '20px', color: 'white', cursor: 'pointer' }} />
        </Space>
      </Header>

      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        {loading ? (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '70vh'
          }}>
            <Spin size="large" tip="连接服务器..." />
          </div>
        ) : (
          <Dashboard connected={connected} />
        )}
      </Content>

      <Footer style={{ textAlign: 'center', background: '#001529', color: 'white' }}>
        MCP Enterprise Server v2.1.0 © 2025 - Phase 4: 管理UI
      </Footer>
    </Layout>
  );
}

export default App;
