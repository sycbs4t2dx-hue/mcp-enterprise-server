import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Input,
  Select,
  Drawer,
  Descriptions,
  Row,
  Col,
  Progress,
  Alert,
  Badge,
  Tabs,
  Timeline,
  Statistic,
  Modal,
  Form,
  message,
  Tooltip,
  Empty
} from 'antd';
import {
  CodeOutlined,
  SearchOutlined,
  FilterOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ExportOutlined,
  ImportOutlined,
  StarOutlined,
  StarFilled,
  BulbOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  RiseOutlined,
  FallOutlined
} from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './PatternLibrary.css';

const { Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;
const { TextArea } = Input;

interface Pattern {
  pattern_id: string;
  pattern_type: string;
  pattern_name: string;
  pattern_category: string;
  pattern_description: string;
  pattern_template: string;
  features: Array<{
    feature_type: string;
    feature_name: string;
    feature_value: any;
    weight: number;
    confidence: number;
  }>;
  keywords: string[];
  success_rate: number;
  effectiveness: number;
  evolution_stage: number;
  usage_count: number;
  created_at: string;
  updated_at: string;
  tags: string[];
}

interface PatternStatistics {
  total_patterns: number;
  design_patterns: number;
  anti_patterns: number;
  code_smells: number;
  optimizations: number;
  avg_effectiveness: number;
  avg_success_rate: number;
  most_used_pattern: string;
  recently_evolved: number;
}

const PatternLibrary: React.FC = () => {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [filteredPatterns, setFilteredPatterns] = useState<Pattern[]>([]);
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);
  const [statistics, setStatistics] = useState<PatternStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [importModalVisible, setImportModalVisible] = useState(false);

  // 过滤器状态
  const [searchText, setSearchText] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [minEffectiveness, setMinEffectiveness] = useState<number>(0);
  const [favoritePatterns, setFavoritePatterns] = useState<Set<string>>(new Set());

  // 加载模式库
  const loadPatterns = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8765/api/patterns/library');
      if (response.ok) {
        const data = await response.json();
        setPatterns(data.patterns || []);
        setFilteredPatterns(data.patterns || []);
        setStatistics(data.statistics);
      }
    } catch (error) {
      console.error('Failed to load patterns:', error);
      message.error('加载模式库失败');
    } finally {
      setLoading(false);
    }
  };

  // 应用过滤器
  useEffect(() => {
    let filtered = [...patterns];

    // 文本搜索
    if (searchText) {
      filtered = filtered.filter(p =>
        p.pattern_name.toLowerCase().includes(searchText.toLowerCase()) ||
        p.pattern_description.toLowerCase().includes(searchText.toLowerCase()) ||
        p.keywords.some(k => k.toLowerCase().includes(searchText.toLowerCase()))
      );
    }

    // 类型过滤
    if (selectedType !== 'all') {
      filtered = filtered.filter(p => p.pattern_type === selectedType);
    }

    // 类别过滤
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(p => p.pattern_category === selectedCategory);
    }

    // 效果过滤
    filtered = filtered.filter(p => p.effectiveness >= minEffectiveness);

    setFilteredPatterns(filtered);
  }, [searchText, selectedType, selectedCategory, minEffectiveness, patterns]);

  useEffect(() => {
    loadPatterns();

    // 从localStorage加载收藏
    const saved = localStorage.getItem('favoritePatterns');
    if (saved) {
      setFavoritePatterns(new Set(JSON.parse(saved)));
    }
  }, []);

  // 切换收藏
  const toggleFavorite = (patternId: string) => {
    const newFavorites = new Set(favoritePatterns);
    if (newFavorites.has(patternId)) {
      newFavorites.delete(patternId);
    } else {
      newFavorites.add(patternId);
    }
    setFavoritePatterns(newFavorites);
    localStorage.setItem('favoritePatterns', JSON.stringify(Array.from(newFavorites)));
  };

  // 导出模式
  const exportPattern = (pattern: Pattern) => {
    const dataStr = JSON.stringify(pattern, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = `pattern_${pattern.pattern_name}_${Date.now()}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();

    message.success('模式导出成功');
  };

  // 删除模式
  const deletePattern = async (patternId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个模式吗？此操作不可恢复。',
      onOk: async () => {
        try {
          const response = await fetch(`http://localhost:8765/api/patterns/${patternId}`, {
            method: 'DELETE'
          });
          if (response.ok) {
            message.success('模式删除成功');
            loadPatterns();
          }
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  // 表格列定义
  const columns = [
    {
      title: '模式名称',
      dataIndex: 'pattern_name',
      key: 'pattern_name',
      render: (text: string, record: Pattern) => (
        <Space>
          <Button
            type="link"
            icon={<CodeOutlined />}
            onClick={() => {
              setSelectedPattern(record);
              setDrawerVisible(true);
            }}
          >
            {text}
          </Button>
          {favoritePatterns.has(record.pattern_id) && <StarFilled style={{ color: '#faad14' }} />}
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'pattern_type',
      key: 'pattern_type',
      render: (type: string) => {
        const colorMap: any = {
          'design_pattern': 'blue',
          'anti_pattern': 'red',
          'code_smell': 'orange',
          'optimization': 'green',
          'idiom': 'purple'
        };
        const iconMap: any = {
          'design_pattern': <BulbOutlined />,
          'anti_pattern': <WarningOutlined />,
          'code_smell': <WarningOutlined />,
          'optimization': <RiseOutlined />
        };
        return (
          <Tag color={colorMap[type]} icon={iconMap[type]}>
            {type.replace('_', ' ').toUpperCase()}
          </Tag>
        );
      }
    },
    {
      title: '类别',
      dataIndex: 'pattern_category',
      key: 'pattern_category',
      render: (category: string) => <Tag>{category}</Tag>
    },
    {
      title: '有效性',
      dataIndex: 'effectiveness',
      key: 'effectiveness',
      render: (value: number) => (
        <Progress
          percent={Math.round(value * 100)}
          size="small"
          strokeColor={{
            '0%': '#108ee9',
            '100%': '#87d068',
          }}
        />
      )
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      render: (value: number) => (
        <Tooltip title={`基于 ${value} 次使用`}>
          <span>{(value * 100).toFixed(1)}%</span>
        </Tooltip>
      )
    },
    {
      title: '演化阶段',
      dataIndex: 'evolution_stage',
      key: 'evolution_stage',
      render: (stage: number) => (
        <Badge count={stage} style={{ backgroundColor: stage > 3 ? '#52c41a' : '#1890ff' }} />
      )
    },
    {
      title: '使用次数',
      dataIndex: 'usage_count',
      key: 'usage_count',
      sorter: (a: Pattern, b: Pattern) => a.usage_count - b.usage_count
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space size="small" wrap>
          {tags.slice(0, 3).map(tag => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
          {tags.length > 3 && <Tag>+{tags.length - 3}</Tag>}
        </Space>
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Pattern) => (
        <Space>
          <Tooltip title="收藏">
            <Button
              type="text"
              icon={favoritePatterns.has(record.pattern_id) ? <StarFilled /> : <StarOutlined />}
              onClick={() => toggleFavorite(record.pattern_id)}
            />
          </Tooltip>
          <Tooltip title="导出">
            <Button
              type="text"
              icon={<ExportOutlined />}
              onClick={() => exportPattern(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => {
                setSelectedPattern(record);
                setEditModalVisible(true);
              }}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => deletePattern(record.pattern_id)}
            />
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <div className="pattern-library">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总模式数"
              value={statistics?.total_patterns || 0}
              prefix={<CodeOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均有效性"
              value={(statistics?.avg_effectiveness || 0) * 100}
              precision={1}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均成功率"
              value={(statistics?.avg_success_rate || 0) * 100}
              precision={1}
              suffix="%"
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最近演化"
              value={statistics?.recently_evolved || 0}
              prefix={<SyncOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      {/* 主卡片 */}
      <Card
        title={
          <Space>
            <CodeOutlined />
            <span>模式库</span>
            <Badge count={filteredPatterns.length} showZero />
          </Space>
        }
        extra={
          <Space>
            <Button icon={<PlusOutlined />} type="primary">添加模式</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportModalVisible(true)}>
              导入
            </Button>
            <Button icon={<SyncOutlined />} onClick={loadPatterns}>
              刷新
            </Button>
          </Space>
        }
      >
        {/* 过滤器 */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Search
            placeholder="搜索模式..."
            style={{ width: 200 }}
            onSearch={setSearchText}
            onChange={e => setSearchText(e.target.value)}
          />

          <Select
            style={{ width: 150 }}
            placeholder="类型"
            value={selectedType}
            onChange={setSelectedType}
          >
            <Option value="all">全部类型</Option>
            <Option value="design_pattern">设计模式</Option>
            <Option value="anti_pattern">反模式</Option>
            <Option value="code_smell">代码异味</Option>
            <Option value="optimization">优化模式</Option>
          </Select>

          <Select
            style={{ width: 150 }}
            placeholder="类别"
            value={selectedCategory}
            onChange={setSelectedCategory}
          >
            <Option value="all">全部类别</Option>
            <Option value="structural">结构型</Option>
            <Option value="behavioral">行为型</Option>
            <Option value="creational">创建型</Option>
            <Option value="performance">性能</Option>
            <Option value="quality">质量</Option>
          </Select>

          <span>最低有效性:</span>
          <Select
            style={{ width: 100 }}
            value={minEffectiveness}
            onChange={setMinEffectiveness}
          >
            <Option value={0}>不限</Option>
            <Option value={0.5}>50%</Option>
            <Option value={0.6}>60%</Option>
            <Option value={0.7}>70%</Option>
            <Option value={0.8}>80%</Option>
            <Option value={0.9}>90%</Option>
          </Select>

          <Button
            type={favoritePatterns.size > 0 ? 'primary' : 'default'}
            icon={<StarOutlined />}
            onClick={() => {
              if (favoritePatterns.size > 0) {
                setFilteredPatterns(patterns.filter(p => favoritePatterns.has(p.pattern_id)));
              } else {
                setFilteredPatterns(patterns);
              }
            }}
          >
            收藏 ({favoritePatterns.size})
          </Button>
        </Space>

        {/* 模式表格 */}
        <Table
          columns={columns}
          dataSource={filteredPatterns}
          rowKey="pattern_id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 个模式`
          }}
        />
      </Card>

      {/* 模式详情抽屉 */}
      <Drawer
        title={selectedPattern?.pattern_name}
        placement="right"
        width={800}
        onClose={() => setDrawerVisible(false)}
        visible={drawerVisible}
      >
        {selectedPattern && (
          <div>
            <Descriptions bordered column={1} style={{ marginBottom: 24 }}>
              <Descriptions.Item label="ID">{selectedPattern.pattern_id}</Descriptions.Item>
              <Descriptions.Item label="类型">
                <Tag>{selectedPattern.pattern_type}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="类别">
                <Tag>{selectedPattern.pattern_category}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="描述">
                {selectedPattern.pattern_description}
              </Descriptions.Item>
              <Descriptions.Item label="关键词">
                <Space wrap>
                  {selectedPattern.keywords.map(k => (
                    <Tag key={k} color="blue">{k}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="标签">
                <Space wrap>
                  {selectedPattern.tags.map(t => (
                    <Tag key={t}>{t}</Tag>
                  ))}
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <Tabs defaultActiveKey="template">
              <TabPane tab="模板代码" key="template">
                {selectedPattern.pattern_template ? (
                  <SyntaxHighlighter
                    language="python"
                    style={vscDarkPlus}
                    showLineNumbers
                  >
                    {selectedPattern.pattern_template}
                  </SyntaxHighlighter>
                ) : (
                  <Empty description="暂无模板代码" />
                )}
              </TabPane>

              <TabPane tab="特征" key="features">
                <Table
                  dataSource={selectedPattern.features}
                  columns={[
                    { title: '类型', dataIndex: 'feature_type', key: 'feature_type' },
                    { title: '名称', dataIndex: 'feature_name', key: 'feature_name' },
                    {
                      title: '值',
                      dataIndex: 'feature_value',
                      key: 'feature_value',
                      render: (v: any) => JSON.stringify(v)
                    },
                    {
                      title: '权重',
                      dataIndex: 'weight',
                      key: 'weight',
                      render: (w: number) => w.toFixed(2)
                    },
                    {
                      title: '置信度',
                      dataIndex: 'confidence',
                      key: 'confidence',
                      render: (c: number) => `${(c * 100).toFixed(0)}%`
                    }
                  ]}
                  rowKey={(r, i) => `${r.feature_type}_${r.feature_name}_${i}`}
                  pagination={false}
                />
              </TabPane>

              <TabPane tab="使用统计" key="statistics">
                <Row gutter={[16, 16]}>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="使用次数"
                        value={selectedPattern.usage_count}
                        prefix={<ClockCircleOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="成功率"
                        value={selectedPattern.success_rate * 100}
                        precision={1}
                        suffix="%"
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="演化阶段"
                        value={selectedPattern.evolution_stage}
                        prefix={<SyncOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>

                <Card style={{ marginTop: 16 }} title="演化历史">
                  <Timeline>
                    <Timeline.Item color="green">
                      创建于 {new Date(selectedPattern.created_at).toLocaleDateString()}
                    </Timeline.Item>
                    {selectedPattern.evolution_stage > 1 && (
                      <Timeline.Item color="blue">
                        演化到阶段 2 - 优化性能
                      </Timeline.Item>
                    )}
                    {selectedPattern.evolution_stage > 2 && (
                      <Timeline.Item color="blue">
                        演化到阶段 3 - 增强功能
                      </Timeline.Item>
                    )}
                    <Timeline.Item>
                      最后更新 {new Date(selectedPattern.updated_at).toLocaleDateString()}
                    </Timeline.Item>
                  </Timeline>
                </Card>
              </TabPane>
            </Tabs>
          </div>
        )}
      </Drawer>

      {/* 编辑模式Modal */}
      <Modal
        title="编辑模式"
        visible={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        width={800}
        footer={null}
      >
        {selectedPattern && (
          <Form
            layout="vertical"
            initialValues={selectedPattern}
            onFinish={async (values) => {
              try {
                const response = await fetch(
                  `http://localhost:8765/api/patterns/${selectedPattern.pattern_id}`,
                  {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(values)
                  }
                );
                if (response.ok) {
                  message.success('模式更新成功');
                  setEditModalVisible(false);
                  loadPatterns();
                }
              } catch (error) {
                message.error('更新失败');
              }
            }}
          >
            <Form.Item label="模式名称" name="pattern_name" rules={[{ required: true }]}>
              <Input />
            </Form.Item>
            <Form.Item label="描述" name="pattern_description">
              <TextArea rows={3} />
            </Form.Item>
            <Form.Item label="模板代码" name="pattern_template">
              <TextArea rows={10} style={{ fontFamily: 'monospace' }} />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit">保存</Button>
                <Button onClick={() => setEditModalVisible(false)}>取消</Button>
              </Space>
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* 导入模式Modal */}
      <Modal
        title="导入模式"
        visible={importModalVisible}
        onCancel={() => setImportModalVisible(false)}
        footer={null}
      >
        <Alert
          message="支持JSON格式的模式文件"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <input
          type="file"
          accept=".json"
          onChange={async (e) => {
            const file = e.target.files?.[0];
            if (file) {
              const reader = new FileReader();
              reader.onload = async (event) => {
                try {
                  const pattern = JSON.parse(event.target?.result as string);
                  const response = await fetch('http://localhost:8765/api/patterns/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(pattern)
                  });
                  if (response.ok) {
                    message.success('模式导入成功');
                    setImportModalVisible(false);
                    loadPatterns();
                  }
                } catch (error) {
                  message.error('导入失败：文件格式错误');
                }
              };
              reader.readAsText(file);
            }
          }}
        />
      </Modal>
    </div>
  );
};

export default PatternLibrary;