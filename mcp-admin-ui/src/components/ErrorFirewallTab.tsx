/**
 * 错误防火墙Tab - 错误拦截监控
 */

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Alert, List, Tag, Badge } from 'antd';
import { FireOutlined, CheckCircleOutlined, CloseCircleOutlined, BulbOutlined } from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { PieChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { getWebSocketClient } from '../services/websocket';
import type { ErrorFirewallEvent, WSMessage } from '../types';

echarts.use([PieChart, GridComponent, TooltipComponent, TitleComponent, LegendComponent, CanvasRenderer]);

interface ErrorFirewallTabProps {
  connected: boolean;
}

const ErrorFirewallTab: React.FC<ErrorFirewallTabProps> = ({ connected }) => {
  const [events, setEvents] = useState<ErrorFirewallEvent[]>([]);
  const [blockedCount, setBlockedCount] = useState(0);
  const [passedCount, setPassedCount] = useState(0);

  useEffect(() => {
    const wsClient = getWebSocketClient();
    const unsubscribe = wsClient.onMessage((message: WSMessage) => {
      if (message.channel === 'error_firewall' && message.data) {
        // 处理错误记录通知 (error_recorded) 或拦截通知 (error_intercepted)
        const isIntercept = message.type === 'error_intercepted';

        const event: ErrorFirewallEvent = {
          error_id: message.data.error_id || 'unknown',
          error_scene: message.data.error_scene || message.data.message || 'unknown',
          error_type: message.data.error_type || message.data.operation_type || 'unknown',
          solution: message.data.solution || 'No solution provided',
          confidence: message.data.confidence || message.data.match_confidence || 0,
          timestamp: message.timestamp || new Date().toISOString(),
          status: isIntercept && message.data.action === 'blocked' ? 'blocked' : 'passed'
        };

        setEvents(prev => [event, ...prev].slice(0, 20));
        if (event.status === 'blocked') {
          setBlockedCount(prev => prev + 1);
        } else {
          setPassedCount(prev => prev + 1);
        }
      }
    });

    return unsubscribe;
  }, []);

  const pieOption = {
    title: { text: '拦截统计', left: 'center' },
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [{
      name: '错误状态',
      type: 'pie',
      radius: '50%',
      data: [
        { value: blockedCount, name: '已拦截', itemStyle: { color: '#52c41a' } },
        { value: passedCount, name: '已放行', itemStyle: { color: '#faad14' } }
      ],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  };

  return (
    <div>
      {!connected && <Alert message="WebSocket未连接" type="warning" showIcon style={{ marginBottom: 16 }} />}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="拦截成功"
              value={blockedCount}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="放行错误"
              value={passedCount}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="拦截率"
              value={blockedCount + passedCount > 0 ? (blockedCount / (blockedCount + passedCount)) * 100 : 0}
              suffix="%"
              precision={1}
              prefix={<FireOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card>
            <ReactEChartsCore echarts={echarts} option={pieOption} style={{ height: '300px' }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="实时拦截事件" extra={<Badge status="processing" text="实时更新" />}>
            <List
              dataSource={events}
              renderItem={item => (
                <List.Item>
                  <List.Item.Meta
                    avatar={
                      item.status === 'blocked' ?
                        <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} /> :
                        <BulbOutlined style={{ fontSize: 24, color: '#faad14' }} />
                    }
                    title={
                      <span>
                        {item.error_id}
                        <Tag color={item.status === 'blocked' ? 'green' : 'orange'} style={{ marginLeft: 8 }}>
                          {item.status === 'blocked' ? '已拦截' : '已放行'}
                        </Tag>
                      </span>
                    }
                    description={
                      <div>
                        <div style={{ marginBottom: 4 }}>
                          <Tag color="blue">{item.error_scene}</Tag>
                          <Tag>{item.error_type}</Tag>
                          <span style={{ marginLeft: 8, color: '#999' }}>置信度: {(item.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div style={{ color: '#666', fontSize: 12 }}>
                          {item.solution}
                        </div>
                        <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                          {new Date(item.timestamp).toLocaleString()}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
              style={{ maxHeight: '400px', overflow: 'auto' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ErrorFirewallTab;
