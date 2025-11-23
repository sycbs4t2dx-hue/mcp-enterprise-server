/**
 * 连接池监控Tab - 实时连接池状态和性能图表
 */

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Progress, Alert, Table } from 'antd';
import {
  DatabaseOutlined,
  RiseOutlined,
  FallOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { LineChart, GaugeChart } from 'echarts/charts';
import {
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { getWebSocketClient } from '../services/websocket';
import type { PoolStats, WSMessage } from '../types';

echarts.use([
  LineChart,
  GaugeChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  LegendComponent,
  CanvasRenderer
]);

interface ConnectionPoolTabProps {
  connected: boolean;
}

const ConnectionPoolTab: React.FC<ConnectionPoolTabProps> = ({ connected }) => {
  const [poolStats, setPoolStats] = useState<PoolStats>({
    pool_size: 20,
    active_connections: 0,
    idle_connections: 20,
    overflow_connections: 0,
    utilization: 0,
    qps: 0,
    avg_query_time: 0,
    max_wait_time: 0,
    total_queries: 0,
    timestamp: new Date().toISOString()
  });

  const [history, setHistory] = useState<{
    time: string[];
    utilization: number[];
    qps: number[];
    avgQueryTime: number[];
  }>(() => {
    // 从 localStorage 恢复历史数据
    try {
      const saved = localStorage.getItem('pool_chart_data');
      if (saved) {
        const parsed = JSON.parse(saved);
        console.log('📊 从 localStorage 恢复连接池图表数据');
        return parsed;
      }
    } catch (e) {
      console.error('恢复连接池图表数据失败:', e);
    }
    return {
      time: [],
      utilization: [],
      qps: [],
      avgQueryTime: []
    };
  });

  // 调整历史记录 - 动态从WebSocket接收
  const [adjustmentHistory, setAdjustmentHistory] = useState<Array<{
    key: string;
    time: string;
    action: string;
    from: number;
    to: number;
    reason: string;
  }>>([]);

  useEffect(() => {
    const wsClient = getWebSocketClient();

    // 获取初始连接池统计
    fetch('http://localhost:8765/api/pool/stats')
      .then(res => res.json())
      .then(data => {
        setPoolStats(data);
        console.log('✅ 连接池初始数据加载成功:', data);
      })
      .catch(err => {
        console.error('❌ 连接池初始数据加载失败:', err);
      });

    const unsubscribe = wsClient.onMessage((message: WSMessage) => {
      if (message.channel === 'db_pool_stats') {
        // 处理统计更新
        if (message.type === 'stats_update' && message.data) {
          setPoolStats(prev => ({
            ...prev,
            ...message.data,
            timestamp: message.timestamp || new Date().toISOString()
          }));

          // 更新历史数据
          setHistory(prev => {
            const now = new Date().toLocaleTimeString();
            const newData = {
              time: [...prev.time, now].slice(-30),
              utilization: [...prev.utilization, message.data.utilization || 0].slice(-30),
              qps: [...prev.qps, message.data.qps || 0].slice(-30),
              avgQueryTime: [...prev.avgQueryTime, message.data.avg_query_time || 0].slice(-30)
            };

            // 保存到 localStorage
            try {
              localStorage.setItem('pool_chart_data', JSON.stringify(newData));
            } catch (e) {
              console.error('保存连接池图表数据失败:', e);
            }

            return newData;
          });
        }

        // 处理调整历史
        if (message.type === 'pool_adjusted' && message.data) {
          const adjustment = {
            key: `${Date.now()}`,
            time: new Date(message.data.timestamp).toLocaleTimeString(),
            action: message.data.action,
            from: message.data.from,
            to: message.data.to,
            reason: message.data.reason
          };

          setAdjustmentHistory(prev => [adjustment, ...prev].slice(0, 20));
          console.log('📊 连接池调整:', adjustment);
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const utilizationGaugeOption = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: 0,
        max: 100,
        splitNumber: 8,
        axisLine: {
          lineStyle: {
            width: 6,
            color: [
              [0.6, '#52c41a'],
              [0.8, '#faad14'],
              [1, '#ff4d4f']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 20,
          offsetCenter: [0, '-60%'],
          itemStyle: {
            color: 'auto'
          }
        },
        axisTick: {
          length: 12,
          lineStyle: {
            color: 'auto',
            width: 2
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 5
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 12,
          distance: -60,
          formatter: function (value: number) {
            return value + '%';
          }
        },
        title: {
          offsetCenter: [0, '-20%'],
          fontSize: 16,
          color: '#464646'
        },
        detail: {
          fontSize: 24,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: function (value: number) {
            return Math.round(value) + '%';
          },
          color: 'auto'
        },
        data: [
          {
            value: poolStats.utilization,
            name: '连接池使用率'
          }
        ]
      }
    ]
  };

  const metricsOption = {
    title: {
      text: '性能指标趋势',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['使用率(%)', 'QPS', '平均查询时间(ms)'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: history.time
    },
    yAxis: [
      {
        type: 'value',
        name: '使用率/QPS',
        position: 'left'
      },
      {
        type: 'value',
        name: '查询时间(ms)',
        position: 'right'
      }
    ],
    series: [
      {
        name: '使用率(%)',
        type: 'line',
        data: history.utilization,
        smooth: true,
        itemStyle: { color: '#1890ff' }
      },
      {
        name: 'QPS',
        type: 'line',
        data: history.qps,
        smooth: true,
        itemStyle: { color: '#52c41a' }
      },
      {
        name: '平均查询时间(ms)',
        type: 'line',
        yAxisIndex: 1,
        data: history.avgQueryTime,
        smooth: true,
        itemStyle: { color: '#faad14' }
      }
    ]
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time'
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (text: string) => (
        <span style={{ color: text.includes('扩容') ? '#52c41a' : '#faad14' }}>
          {text}
        </span>
      )
    },
    {
      title: '调整',
      key: 'adjustment',
      render: (_: any, record: any) => `${record.from} → ${record.to}`
    },
    {
      title: '原因',
      dataIndex: 'reason',
      key: 'reason'
    }
  ];

  return (
    <div>
      {!connected && (
        <Alert
          message="WebSocket未连接"
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
              title="连接池大小"
              value={poolStats.pool_size}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃连接"
              value={poolStats.active_connections}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="空闲连接"
              value={poolStats.idle_connections}
              prefix={<FallOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="QPS"
              value={poolStats.qps}
              prefix={<ThunderboltOutlined />}
              precision={0}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 进度条 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="连接池使用情况">
            <div style={{ marginBottom: 16 }}>
              <span>活跃连接</span>
              <Progress
                percent={Math.round((poolStats.active_connections / poolStats.pool_size) * 100)}
                status="active"
                strokeColor="#52c41a"
              />
            </div>
            <div>
              <span>总使用率</span>
              <Progress
                percent={Math.round(poolStats.utilization)}
                strokeColor={
                  poolStats.utilization > 80 ? '#ff4d4f' :
                  poolStats.utilization > 60 ? '#faad14' : '#52c41a'
                }
              />
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="性能指标">
            <Row>
              <Col span={12}>
                <Statistic
                  title="平均查询时间"
                  value={poolStats.avg_query_time}
                  suffix="ms"
                  precision={2}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="最大等待时间"
                  value={poolStats.max_wait_time}
                  suffix="ms"
                  precision={2}
                />
              </Col>
            </Row>
            <Row style={{ marginTop: 16 }}>
              <Col span={24}>
                <Statistic
                  title="总查询数"
                  value={poolStats.total_queries}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* ECharts图表 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card>
            <ReactEChartsCore
              echarts={echarts}
              option={utilizationGaugeOption}
              style={{ height: '350px' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card>
            <ReactEChartsCore
              echarts={echarts}
              option={metricsOption}
              style={{ height: '350px' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 调整历史 */}
      <Card title="连接池调整历史">
        <Table
          columns={columns}
          dataSource={adjustmentHistory}
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  );
};

export default ConnectionPoolTab;
