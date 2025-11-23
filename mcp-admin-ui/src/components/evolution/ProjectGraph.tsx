import React, { useEffect, useRef, useState } from 'react';
import { Card, Row, Col, Spin, Alert, Button, Select, Slider, Statistic, Tag, Tooltip, Space } from 'antd';
import {
  PartitionOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  ClusterOutlined,
  HeatMapOutlined,
  BranchesOutlined
} from '@ant-design/icons';
import * as d3 from 'd3';
import './ProjectGraph.css';

const { Option } = Select;

interface GraphNode {
  id: string;
  name: string;
  type: string;
  x: number;
  y: number;
  z: number;
  size: number;
  color: string;
  cluster: string;
  complexity: number;
  importance: number;
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  weight: number;
  color: string;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  clusters: any[];
  layers: any[];
  statistics: {
    total_nodes: number;
    class_count: number;
    function_count: number;
    avg_complexity: number;
    max_importance: number;
  };
}

const ProjectGraph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // 视图控制
  const [viewMode, setViewMode] = useState<'2d' | '3d' | 'hierarchy'>('2d');
  const [layoutType, setLayoutType] = useState<'force' | 'circular' | 'hierarchical'>('force');
  const [showClusters, setShowClusters] = useState(true);
  const [showComplexity, setShowComplexity] = useState(false);
  const [filterThreshold, setFilterThreshold] = useState(0);
  const [zoom, setZoom] = useState(1);

  // 生成项目图谱
  const generateGraph = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:8765/api/evolution/graph/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_path: '/Users/mac/Downloads/MCP',
          max_depth: 10,
          min_importance: 0.1
        })
      });

      if (!response.ok) throw new Error('Failed to generate graph');

      // 等待生成完成
      await new Promise(resolve => setTimeout(resolve, 3000));

      // 获取生成的图谱
      const dataResponse = await fetch('http://localhost:8765/api/evolution/graph/default');
      if (!dataResponse.ok) throw new Error('Failed to fetch graph data');

      const data = await dataResponse.json();
      setGraphData(data.graph);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 渲染D3图谱
  const renderGraph = () => {
    if (!graphData || !svgRef.current || !containerRef.current) return;

    const container = containerRef.current;
    const width = container.clientWidth;
    const height = container.clientHeight || 600;

    // 清除旧图
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height);

    // 创建缩放容器
    const g = svg.append('g');

    // 过滤节点
    const filteredNodes = graphData.nodes.filter(n => n.importance >= filterThreshold);
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredEdges = graphData.edges.filter(e =>
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    // 创建力导向图
    const simulation = d3.forceSimulation(filteredNodes)
      .force('link', d3.forceLink(filteredEdges)
        .id((d: any) => d.id)
        .distance(50)
        .strength((d: any) => d.weight))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d: any) => d.size * 5));

    // 绘制边
    const links = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(filteredEdges)
      .enter().append('line')
      .attr('stroke', d => d.color)
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', d => Math.sqrt(d.weight));

    // 绘制节点
    const nodes = g.append('g')
      .attr('class', 'nodes')
      .selectAll('circle')
      .data(filteredNodes)
      .enter().append('circle')
      .attr('r', d => d.size * 5)
      .attr('fill', d => d.color)
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .on('click', (event, d) => setSelectedNode(d))
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended) as any);

    // 添加标签
    const labels = g.append('g')
      .attr('class', 'labels')
      .selectAll('text')
      .data(filteredNodes)
      .enter().append('text')
      .text(d => d.name)
      .attr('font-size', 10)
      .attr('dx', 12)
      .attr('dy', 4);

    // 如果显示聚类
    if (showClusters && graphData.clusters.length > 0) {
      // 绘制聚类边界
      const clusterGroups = d3.group(filteredNodes, d => d.cluster);
      const hulls = g.append('g')
        .attr('class', 'hulls')
        .selectAll('path')
        .data(Array.from(clusterGroups.values()))
        .enter().append('path')
        .attr('fill', (d, i) => d3.schemeCategory10[i % 10])
        .attr('fill-opacity', 0.1)
        .attr('stroke', (d, i) => d3.schemeCategory10[i % 10])
        .attr('stroke-opacity', 0.3)
        .attr('stroke-width', 2);
    }

    // 如果显示复杂度热力图
    if (showComplexity) {
      nodes.attr('fill-opacity', d => 0.3 + d.complexity * 0.7);
    }

    // 更新位置
    simulation.on('tick', () => {
      links
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      nodes
        .attr('cx', (d: any) => d.x)
        .attr('cy', (d: any) => d.y);

      labels
        .attr('x', (d: any) => d.x)
        .attr('y', (d: any) => d.y);
    });

    // 缩放功能
    const zoomBehavior = d3.zoom()
      .scaleExtent([0.1, 10])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        setZoom(event.transform.k);
      });

    svg.call(zoomBehavior as any);

    // 拖拽函数
    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }
  };

  useEffect(() => {
    if (graphData) {
      renderGraph();
    }
  }, [graphData, showClusters, showComplexity, filterThreshold, layoutType]);

  // 处理窗口大小变化
  useEffect(() => {
    const handleResize = () => renderGraph();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [graphData]);

  return (
    <div className="project-graph">
      <Card
        title={
          <Space>
            <PartitionOutlined />
            <span>项目知识图谱</span>
          </Space>
        }
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={generateGraph}
              loading={loading}
            >
              生成图谱
            </Button>
            <Button icon={<FullscreenOutlined />}>全屏</Button>
          </Space>
        }
      >
        {/* 控制面板 */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card size="small" title="视图控制">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Select
                  value={viewMode}
                  onChange={setViewMode}
                  style={{ width: '100%' }}
                >
                  <Option value="2d">2D视图</Option>
                  <Option value="3d">3D视图</Option>
                  <Option value="hierarchy">层级视图</Option>
                </Select>

                <Select
                  value={layoutType}
                  onChange={setLayoutType}
                  style={{ width: '100%' }}
                >
                  <Option value="force">力导向布局</Option>
                  <Option value="circular">环形布局</Option>
                  <Option value="hierarchical">层级布局</Option>
                </Select>

                <div>
                  <span>重要性阈值:</span>
                  <Slider
                    min={0}
                    max={1}
                    step={0.1}
                    value={filterThreshold}
                    onChange={setFilterThreshold}
                  />
                </div>
              </Space>
            </Card>
          </Col>

          <Col span={6}>
            <Card size="small" title="显示选项">
              <Space direction="vertical">
                <Button
                  icon={<ClusterOutlined />}
                  type={showClusters ? 'primary' : 'default'}
                  onClick={() => setShowClusters(!showClusters)}
                >
                  显示聚类
                </Button>
                <Button
                  icon={<HeatMapOutlined />}
                  type={showComplexity ? 'primary' : 'default'}
                  onClick={() => setShowComplexity(!showComplexity)}
                >
                  复杂度热力图
                </Button>
                <Button icon={<BranchesOutlined />}>
                  显示依赖
                </Button>
              </Space>
            </Card>
          </Col>

          <Col span={6}>
            <Card size="small" title="统计信息">
              {graphData && (
                <Space direction="vertical" size="small">
                  <div>节点总数: <Tag>{graphData.statistics.total_nodes}</Tag></div>
                  <div>类数量: <Tag>{graphData.statistics.class_count}</Tag></div>
                  <div>函数数量: <Tag>{graphData.statistics.function_count}</Tag></div>
                  <div>平均复杂度: <Tag>{graphData.statistics.avg_complexity.toFixed(2)}</Tag></div>
                </Space>
              )}
            </Card>
          </Col>

          <Col span={6}>
            <Card size="small" title="选中节点">
              {selectedNode ? (
                <Space direction="vertical" size="small">
                  <div>名称: <Tag>{selectedNode.name}</Tag></div>
                  <div>类型: <Tag>{selectedNode.type}</Tag></div>
                  <div>复杂度: <Tag color="orange">{selectedNode.complexity.toFixed(2)}</Tag></div>
                  <div>重要性: <Tag color="green">{selectedNode.importance.toFixed(2)}</Tag></div>
                </Space>
              ) : (
                <div style={{ color: '#999' }}>未选中节点</div>
              )}
            </Card>
          </Col>
        </Row>

        {/* 图谱显示区 */}
        <div ref={containerRef} style={{ height: 600, position: 'relative' }}>
          {loading && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)'
            }}>
              <Spin size="large" tip="生成图谱中..." />
            </div>
          )}

          {error && (
            <Alert
              message="图谱生成失败"
              description={error}
              type="error"
              showIcon
            />
          )}

          <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />

          {/* 缩放控制 */}
          <div style={{
            position: 'absolute',
            bottom: 20,
            right: 20,
            background: 'white',
            padding: 8,
            borderRadius: 4,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}>
            <Space>
              <Button
                icon={<ZoomInOutlined />}
                size="small"
                onClick={() => setZoom(zoom * 1.2)}
              />
              <span>{(zoom * 100).toFixed(0)}%</span>
              <Button
                icon={<ZoomOutOutlined />}
                size="small"
                onClick={() => setZoom(zoom * 0.8)}
              />
            </Space>
          </div>
        </div>

        {/* 图例 */}
        <Card size="small" title="图例" style={{ marginTop: 16 }}>
          <Space size="large">
            <span><span style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#FF6B6B',
              marginRight: 4
            }} /> 模块</span>
            <span><span style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#4ECDC4',
              marginRight: 4
            }} /> 类</span>
            <span><span style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#45B7D1',
              marginRight: 4
            }} /> 函数</span>
            <span><span style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#96CEB4',
              marginRight: 4
            }} /> 方法</span>
            <span><span style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: '#FFEAA7',
              marginRight: 4
            }} /> 变量</span>
          </Space>
        </Card>
      </Card>
    </div>
  );
};

export default ProjectGraph;