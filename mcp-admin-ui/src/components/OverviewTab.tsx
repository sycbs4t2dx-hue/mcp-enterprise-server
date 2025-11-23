/**
 * 系统概览Tab - 实时统计和活动日志
 */

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, List, Tag, Alert } from 'antd';
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  RiseOutlined
} from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { LineChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { getWebSocketClient } from '../services/websocket';
import type { OverviewStats, ActivityLog, WSMessage } from '../types';

// 注册ECharts组件
echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer
]);

interface OverviewTabProps {
  connected: boolean;
}

const OverviewTab: React.FC<OverviewTabProps> = ({ connected }) => {
  const [stats, setStats] = useState<OverviewStats>({
    total_requests: 0,
    successful_requests: 0,
    failed_requests: 0,
    avg_response_time: 0,
    active_connections: 0,
    memory_usage: 0,
    cpu_usage: 0,
    uptime: 0,
    timestamp: new Date().toISOString()
  });

  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [chartData, setChartData] = useState<{
    time: string[];
    requests: number[];
    responseTime: number[];
  }>(() => {
    // 从 localStorage 恢复历史数据
    try {
      const saved = localStorage.getItem('overview_chart_data');
      if (saved) {
        const parsed = JSON.parse(saved);
        console.log('📊 从 localStorage 恢复图表数据');
        return parsed;
      }
    } catch (e) {
      console.error('恢复图表数据失败:', e);
    }
    return {
      time: [],
      requests: [],
      responseTime: []
    };
  });

  useEffect(() => {
    const wsClient = getWebSocketClient();

    // 获取初始统计数据
    fetch('http://localhost:8765/api/overview/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        console.log('✅ 初始统计数据加载成功:', data);
      })
      .catch(err => {
        console.error('❌ 初始统计数据加载失败:', err);
      });

    // 监听所有频道的消息
    const unsubscribe = wsClient.onMessage((message: WSMessage) => {
      // 处理系统统计消息
      if (message.channel === 'system_stats' && message.data) {
        setStats(prev => ({
          ...prev,
          total_requests: message.data.total_requests ?? prev.total_requests,
          successful_requests: message.data.successful_requests ?? prev.successful_requests,
          failed_requests: message.data.failed_requests ?? prev.failed_requests,
          avg_response_time: message.data.avg_response_time ?? prev.avg_response_time,
          active_connections: message.data.active_connections ?? prev.active_connections,
          memory_usage: message.data.memory_usage ?? prev.memory_usage,
          cpu_usage: message.data.cpu_usage ?? prev.cpu_usage,
          uptime: message.data.uptime ?? prev.uptime,
          timestamp: message.data.timestamp || new Date().toISOString()
        }));

        // 更新图表数据
        setChartData(prev => {
          const now = new Date().toLocaleTimeString();
          const newTime = [...prev.time, now].slice(-20);
          const newRequests = [...prev.requests, message.data.total_requests || 0].slice(-20);
          const newResponseTime = [...prev.responseTime, message.data.avg_response_time || 0].slice(-20);

          const newData = {
            time: newTime,
            requests: newRequests,
            responseTime: newResponseTime
          };

          // 保存到 localStorage
          try {
            localStorage.setItem('overview_chart_data', JSON.stringify(newData));
          } catch (e) {
            console.error('保存图表数据失败:', e);
          }

          return newData;
        });
        return;
      }

      // 添加到活动日志
      const activity: ActivityLog = {
        id: `${Date.now()}-${Math.random()}`,
        type: getActivityType(message.type),
        title: getActivityTitle(message.type, message.channel),
        description: JSON.stringify(message.data).slice(0, 100),
        timestamp: message.timestamp || new Date().toISOString(),
        channel: message.channel || 'system'
      };

      setActivities(prev => [activity, ...prev].slice(0, 50));
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const getActivityType = (type: string): 'info' | 'success' | 'warning' | 'error' => {
    if (type.includes('error')) return 'error';
    if (type.includes('success') || type.includes('completed')) return 'success';
    if (type.includes('warning')) return 'warning';
    return 'info';
  };

  const getActivityTitle = (type: string, channel?: string): string => {
    if (channel === 'error_firewall') return '错误防火墙事件';
    if (channel === 'db_pool_stats') return '连接池调整';
    if (channel === 'vector_search') return '向量检索';
    if (channel === 'system_alerts') return '系统告警';
    return type;
  };

  const requestsOption = {
    title: {
      text: '请求趋势',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: chartData.time
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '请求数',
        type: 'line',
        data: chartData.requests,
        smooth: true,
        areaStyle: {
          color: '#1890ff20'
        }
      }
    ]
  };

  const responseTimeOption = {
    title: {
      text: '响应时间',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: chartData.time
    },
    yAxis: {
      type: 'value',
      name: 'ms'
    },
    series: [
      {
        name: '响应时间',
        type: 'line',
        data: chartData.responseTime,
        smooth: true,
        itemStyle: {
          color: '#52c41a'
        },
        areaStyle: {
          color: '#52c41a20'
        }
      }
    ]
  };

  return (
    <div>
      {!connected && (
        <Alert
          message="WebSocket未连接"
          description="无法接收实时数据更新，部分功能可能不可用"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总请求数"
              value={stats.total_requests}
              prefix={<CloudServerOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功请求"
              value={stats.successful_requests}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败请求"
              value={stats.failed_requests}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均响应时间"
              value={stats.avg_response_time}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃连接"
              value={stats.active_connections}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="内存使用率"
              value={stats.memory_usage}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="CPU使用率"
              value={stats.cpu_usage}
              suffix="%"
              precision={1}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="运行时间"
              value={Math.floor(stats.uptime / 60)}
              suffix="分钟"
            />
          </Card>
        </Col>
      </Row>

      {/* ECharts图表 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <ReactEChartsCore
              echarts={echarts}
              option={requestsOption}
              style={{ height: '300px' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <ReactEChartsCore
              echarts={echarts}
              option={responseTimeOption}
              style={{ height: '300px' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 活动日志 */}
      <Card title="实时活动日志" style={{ marginTop: 16 }}>
        <List
          dataSource={activities}
          renderItem={item => (
            <List.Item>
              <List.Item.Meta
                title={
                  <span>
                    {item.title}
                    <Tag color={
                      item.type === 'error' ? 'red' :
                      item.type === 'success' ? 'green' :
                      item.type === 'warning' ? 'orange' : 'blue'
                    } style={{ marginLeft: 8 }}>
                      {item.channel}
                    </Tag>
                  </span>
                }
                description={
                  <span>
                    {item.description}
                    <span style={{ marginLeft: 16, color: '#999' }}>
                      {new Date(item.timestamp).toLocaleTimeString()}
                    </span>
                  </span>
                }
              />
            </List.Item>
          )}
          style={{ maxHeight: '400px', overflow: 'auto' }}
        />
      </Card>
    </div>
  );
};

export default OverviewTab;
