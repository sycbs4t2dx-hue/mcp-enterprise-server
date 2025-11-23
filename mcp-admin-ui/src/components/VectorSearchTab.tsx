/**
 * 向量检索Tab - Milvus检索统计
 */

import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Alert, Table } from 'antd';
import { SearchOutlined, ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, TitleComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { getWebSocketClient } from '../services/websocket';
import type { VectorSearchStats, WSMessage } from '../types';

echarts.use([BarChart, GridComponent, TooltipComponent, TitleComponent, CanvasRenderer]);

interface VectorSearchTabProps {
  connected: boolean;
}

const VectorSearchTab: React.FC<VectorSearchTabProps> = ({ connected }) => {
  const [stats, setStats] = useState<VectorSearchStats>({
    total_searches: 0,
    avg_search_time: 0,
    p95_search_time: 0,
    p99_search_time: 0,
    recall_rate: 95,
    top_k_distribution: { 5: 0, 10: 0, 20: 0, 50: 0 },
    timestamp: new Date().toISOString()
  });

  // 检索历史记录 - 动态从WebSocket接收
  const [searchHistory, setSearchHistory] = useState<Array<{
    key: string;
    time: string;
    query: string;
    top_k: number;
    time_ms: number;
    results: number;
  }>>([]);

  // 统计Top-K分布
  const [topKCount, setTopKCount] = useState<Record<number, number>>({
    5: 0, 10: 0, 20: 0, 50: 0
  });

  useEffect(() => {
    const wsClient = getWebSocketClient();

    // 获取初始向量检索统计
    fetch('http://localhost:8765/api/vector/stats')
      .then(res => res.json())
      .then(data => {
        setStats(data);
        console.log('✅ 向量检索初始数据加载成功:', data);
      })
      .catch(err => {
        console.error('❌ 向量检索初始数据加载失败:', err);
      });

    const unsubscribe = wsClient.onMessage((message: WSMessage) => {
      if (message.channel === 'vector_search') {
        // 处理检索完成事件
        if (message.type === 'search_completed' && message.data) {
          const record = {
            key: `${Date.now()}`,
            time: new Date(message.data.timestamp).toLocaleTimeString(),
            query: message.data.query,
            top_k: message.data.top_k,
            time_ms: message.data.time_ms,
            results: message.data.results
          };

          // 添加到检索历史
          setSearchHistory(prev => [record, ...prev].slice(0, 50));

          // 更新统计
          setStats(prev => ({
            ...prev,
            total_searches: prev.total_searches + 1,
            avg_search_time: prev.total_searches > 0
              ? (prev.avg_search_time * prev.total_searches + message.data.time_ms) / (prev.total_searches + 1)
              : message.data.time_ms
          }));

          // 更新Top-K分布
          const topK = message.data.top_k;
          setTopKCount(prev => {
            const bucket = topK <= 5 ? 5 : topK <= 10 ? 10 : topK <= 20 ? 20 : 50;
            return {
              ...prev,
              [bucket]: (prev[bucket] || 0) + 1
            };
          });

          console.log('🔍 向量检索完成:', record);
        }

        // 处理统计更新
        if (message.type === 'stats_update' && message.data) {
          setStats(prev => ({ ...prev, ...message.data }));
        }
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const topKOption = {
    title: { text: 'Top-K分布', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: Object.keys(topKCount) },
    yAxis: { type: 'value' },
    series: [{
      name: '查询次数',
      type: 'bar',
      data: Object.values(topKCount),
      itemStyle: { color: '#1890ff' }
    }]
  };

  return (
    <div>
      {!connected && <Alert message="WebSocket未连接" type="warning" showIcon style={{ marginBottom: 16 }} />}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card><Statistic title="总检索次数" value={stats.total_searches} prefix={<SearchOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="平均检索时间" value={stats.avg_search_time} suffix="ms" precision={1} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="P95延迟" value={stats.p95_search_time} suffix="ms" precision={1} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="召回率" value={stats.recall_rate} suffix="%" prefix={<CheckCircleOutlined />} valueStyle={{ color: '#52c41a' }} /></Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card>
            <ReactEChartsCore echarts={echarts} option={topKOption} style={{ height: '300px' }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="检索历史">
            <Table
              columns={[
                { title: '时间', dataIndex: 'time', key: 'time' },
                { title: '查询', dataIndex: 'query', key: 'query' },
                { title: 'Top-K', dataIndex: 'top_k', key: 'top_k' },
                { title: '耗时(ms)', dataIndex: 'time_ms', key: 'time_ms' },
                { title: '结果数', dataIndex: 'results', key: 'results' }
              ]}
              dataSource={searchHistory}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default VectorSearchTab;
